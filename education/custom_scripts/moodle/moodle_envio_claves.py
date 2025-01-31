import requests
import pytz
import frappe
from frappe import _
from datetime import datetime, time as dt_time

@frappe.whitelist()
def send_emails_for_students(course_name):
    """
    Envía correos a los estudiantes detectados con `auth_forcepasswordchange` activado,
    utilizando el correo configurado `no_contestar@atumail.work`.
    """
    log_steps = []
    email_log = []

    try:
        # 1. Obtener el documento del curso
        course_doc = frappe.get_doc("Course", course_name)
        estudiantes_table = course_doc.get("custom_estudiantes")
        if not estudiantes_table:
            raise ValueError("La tabla de estudiantes 'custom_estudiantes' está vacía o no existe en el curso.")
        student_ids = [row.estudiante for row in estudiantes_table if row.estudiante]
        if not student_ids:
            raise ValueError("No se encontraron IDs de estudiantes en la tabla del curso.")

        # 2. Obtener detalles de los estudiantes desde el Doctype `Student`
        students = frappe.get_all(
            "Student",
            filters={"name": ["in", student_ids], "enabled": 1},
            fields=["name", "first_name", "last_name", "dni", "student_email_id"]
        )
        student_map = {student["dni"].lower(): student for student in students}
        log_steps.append(f"Estudiantes del ERP encontrados: {len(students)}")

        # 3. Configuración de Moodle desde `Moodle Instance`
        moodle_instance = frappe.get_doc("Moodle Instance", course_doc.virtual_class)
        moodle_url = moodle_instance.site_url.strip()
        moodle_url = moodle_url if moodle_url.startswith(("http://", "https://")) else f"https://{moodle_url}"
        api_url = f"{moodle_url}/webservice/rest/server.php"
        moodle_token = moodle_instance.api_key
        moodle_name = moodle_instance.site_name

        # 4. Obtener usuarios inscritos en Moodle
        enrolled_users_params = {
            "wstoken": moodle_token,
            "wsfunction": "core_enrol_get_enrolled_users",
            "moodlewsrestformat": "json",
            "courseid": course_doc.moodle_course_code
        }
        enrolled_users_response = requests.get(api_url, params=enrolled_users_params)
        enrolled_users_response.raise_for_status()
        enrolled_users_data = enrolled_users_response.json()
        if not isinstance(enrolled_users_data, list):
            raise ValueError("La respuesta de usuarios inscritos en Moodle no es válida o está vacía.")
        log_steps.append(f"Usuarios inscritos en Moodle obtenidos: {len(enrolled_users_data)}")

        # 5. Verificar `auth_forcepasswordchange` para cada usuario
        users_with_force_password_change = []
        for user in enrolled_users_data:
            username = user.get("username", "").lower()
            user_pref_params = {
                "wstoken": moodle_token,
                "wsfunction": "core_user_get_user_preferences",
                "moodlewsrestformat": "json",
                "userid": user["id"]
            }
            user_pref_response = requests.get(api_url, params=user_pref_params)
            user_pref_response.raise_for_status()
            preferences = user_pref_response.json()
            log_steps.append(f"Preferencias para {username}: {preferences}")

            if isinstance(preferences, dict) and "preferences" in preferences:
                for pref in preferences["preferences"]:
                    if pref.get("name") == "auth_forcepasswordchange" and pref.get("value") == "1":
                        log_steps.append(f"Usuario con auth_forcepasswordchange activado: {username}")
                        users_with_force_password_change.append(user)
                        break

        log_steps.append(f"Usuarios con `auth_forcepasswordchange` activado: {len(users_with_force_password_change)}")

        # 6. Enviar correos
        for user in users_with_force_password_change:
            username = user.get("username", "").lower()
            student = student_map.get(username)
            if not student:
                log_steps.append(f"Usuario Moodle {username} no coincide con estudiantes del ERP.")
                continue

            context = {
                "first_name": student["first_name"],
                "last_name": student["last_name"],
                "username": username,
                "password": username,  # Contraseña es el DNI en minúsculas
                "moodle_name": moodle_name,
                "moodle_url": moodle_url,
            }
            try:
                email_template = frappe.get_doc("Email Template", "alta_alumno_moodle")
                email_content = frappe.render_template(email_template.response, context)
                email_subject = frappe.render_template(email_template.subject, context)

                # Enviar correo
                frappe.sendmail(
                    recipients=[student["student_email_id"]],
                    sender="no_contestar@atumail.work",
                    subject=email_subject,
                    message=email_content
                )

                email_log.append(
                    f"Correo enviado a: {student['student_email_id']}\nAsunto: {email_subject}\n{'-'*50}"
                )
            except Exception as template_error:
                email_log.append(
                    f"Error al procesar o enviar el correo para {student['student_email_id']}:\n{template_error}\n"
                    f"Datos enviados: {context}\n{'-'*50}"
                )
                continue

        log_steps.append(f"Correos enviados a {len(users_with_force_password_change)} usuarios.")

    except Exception as e:
        log_steps.append(f"Error general: {str(e)}")

    # Registrar el log de correos en el sistema
    log_title = f"Envío de Correos para Curso: {course_doc.name if 'course_doc' in locals() else 'Desconocido'}"
    log_body = "\n".join(email_log) or "No se enviaron correos. Revisa los errores en el log detallado:\n" + "\n".join(log_steps)
    frappe.log_error(log_body, log_title)

    return "Envío de correos completado. Revisa el Error Log en ERPNext."
