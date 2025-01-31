import requests
import frappe
import json
from frappe import _

@frappe.whitelist()
def send_emails_to_selected_students(row_numbers, course_name):
    """
    Envía correos a los estudiantes seleccionados si cumplen con `auth_forcepasswordchange` activado en Moodle,
    y registra claramente quién recibió el correo y quién no.
    """
    log_steps = {
        "enviados": [],
        "en_cola": [],
        "no_enviados": []  # Solo guarda los estudiantes que no reciben correo
    }

    try:
        # 1. Obtener el curso usando el campo `course_name`
        course_doc = frappe.get_doc("Course", {"course_name": course_name})
        if not course_doc:
            raise ValueError(f"No se encontró un curso con el nombre '{course_name}'.")

        estudiantes_table = course_doc.get("custom_estudiantes")
        if not estudiantes_table:
            raise ValueError("La tabla de estudiantes 'custom_estudiantes' está vacía o no existe en el curso.")
        
        # Filtrar estudiantes seleccionados por `row_numbers`
        selected_rows = json.loads(row_numbers)
        selected_students = [row for row in estudiantes_table if row.idx in selected_rows]
        student_ids = [row.estudiante for row in selected_students if row.estudiante]

        if not student_ids:
            raise ValueError("No se encontraron IDs de estudiantes seleccionados en la tabla del curso.")

        # 2. Obtener detalles de los estudiantes desde el Doctype `Student`
        students = frappe.get_all(
            "Student",
            filters={"name": ["in", student_ids], "enabled": 1},
            fields=["name", "first_name", "last_name", "dni", "student_email_id"]
        )
        student_map = {student["dni"].lower(): student for student in students}
        selected_dni = set(student_map.keys())  # DNIs seleccionados

        # 3. Configuración de Moodle desde `Moodle Instance`
        moodle_instance = frappe.get_doc("Moodle Instance", course_doc.virtual_class)
        moodle_url = moodle_instance.site_url.strip()
        moodle_url = moodle_url if moodle_url.startswith(("http://", "https://")) else f"https://{moodle_url}"
        api_url = f"{moodle_url}/webservice/rest/server.php"
        moodle_token = moodle_instance.api_key

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

        # Filtrar solo los estudiantes seleccionados que están inscritos en Moodle
        enrolled_students = [
            user for user in enrolled_users_data
            if user.get("username", "").lower() in student_map
        ]
        enrolled_dni = {user.get("username", "").lower() for user in enrolled_students}

        # Identificar usuarios seleccionados pero no inscritos en Moodle
        not_enrolled = selected_dni - enrolled_dni
        log_steps["no_enviados"].extend(not_enrolled)

        # 5. Verificar `auth_forcepasswordchange` para cada usuario
        users_with_force_password_change = []
        for user in enrolled_students:
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

            if isinstance(preferences, dict) and "preferences" in preferences:
                for pref in preferences["preferences"]:
                    if pref.get("name") == "auth_forcepasswordchange" and pref.get("value") == "1":
                        users_with_force_password_change.append(user)
                        break

        # Identificar usuarios inscritos pero sin auth_forcepasswordchange
        no_authforcepassword = enrolled_dni - {user.get("username", "").lower() for user in users_with_force_password_change}
        log_steps["no_enviados"].extend(no_authforcepassword)

        # 6. Enviar correos
        for user in users_with_force_password_change:
            username = user.get("username", "").lower()
            student = student_map.get(username)
            context = {
                "first_name": student["first_name"],
                "last_name": student["last_name"],
                "start_date": course_doc.start_date.strftime("%d-%m-%Y") if course_doc.start_date else "N/A",
                "end_date": course_doc.end_date.strftime("%d-%m-%Y") if course_doc.end_date else "N/A",
                "site_url": moodle_url,
                "dni": student["dni"].lower(),
                "course_name": course_doc.course_name,
            }
            try:
                email_template = frappe.get_doc("Email Template", "E-LEARNING_CP_CREDENCIALES")
                email_content = frappe.render_template(email_template.response, context)
                email_subject = frappe.render_template(email_template.subject, context)

                # Enviar correo
                frappe.sendmail(
                    recipients=[student["student_email_id"]],
                    subject=email_subject,
                    message=email_content
                )
                log_steps["enviados"].append(username)
            except frappe.OutgoingEmailError:
                log_steps["en_cola"].append(username)
            except Exception:
                log_steps["no_enviados"].append(username)

    except Exception as e:
        log_steps["no_enviados"].append(f"Error general: {str(e)}")

    return {"status": "Completado", "log": log_steps}
