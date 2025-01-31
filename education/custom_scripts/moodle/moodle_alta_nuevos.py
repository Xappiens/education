import requests
import pytz
import frappe
from frappe import _
from datetime import datetime, time as dt_time

@frappe.whitelist()
def sync_students_to_moodle_with_email_and_group(course_name):
    """
    Sincroniza estudiantes con Moodle:
    - Solo gestiona alumnos nuevos.
    - Agrega alumnos nuevos al curso.
    - Asocia a estos alumnos nuevos al grupo del curso.
    - Envía correos solo a los nuevos usuarios creados.
    """
    log_steps = []
    email_log = []
    errors = []

    try:
        # Obtener el documento del curso
        course_doc = frappe.get_doc("Course", course_name)
        log_steps.append(f"Curso obtenido: {course_doc.name}")

        # Configuración de Moodle
        moodle_instance = frappe.get_doc("Moodle Instance", course_doc.virtual_class)
        moodle_url = moodle_instance.site_url.strip()
        if not moodle_url.startswith(("http://", "https://")):
            moodle_url = f"https://{moodle_url}"
        api_url = f"{moodle_url}/webservice/rest/server.php"
        moodle_token = moodle_instance.api_key

        # Verificar o crear el grupo
        group_name = f"{course_doc.expediente}_{course_doc.code}_{course_doc.group}"
        group_id = None
        group_params = {
            "wstoken": moodle_token,
            "wsfunction": "core_group_get_course_groups",
            "moodlewsrestformat": "json",
            "courseid": course_doc.moodle_course_code
        }
        group_response = requests.get(api_url, params=group_params)
        group_data = group_response.json()
        if isinstance(group_data, list):
            for group in group_data:
                if group["name"] == group_name:
                    group_id = group["id"]
                    break
        if not group_id:
            create_group_params = {
                "wstoken": moodle_token,
                "wsfunction": "core_group_create_groups",
                "moodlewsrestformat": "json",
                "groups[0][name]": group_name,
                "groups[0][courseid]": course_doc.moodle_course_code,
                "groups[0][description]": f"Grupo para el curso {course_doc.name}"
            }
            create_group_response = requests.post(api_url, data=create_group_params)
            create_group_data = create_group_response.json()
            if isinstance(create_group_data, list) and create_group_data[0].get("id"):
                group_id = create_group_data[0]["id"]

        # Obtener estudiantes habilitados
        student_ids = [entry.estudiante for entry in course_doc.custom_estudiantes if entry.estudiante]
        enabled_students = frappe.get_all(
            "Student",
            filters={"name": ["in", student_ids], "enabled": 1},
            fields=["name", "first_name", "last_name", "dni", "student_mobile_number", "student_email_id"]
        )

        new_users = []  # Para almacenar los nuevos usuarios creados

        # Procesar estudiantes
        for student_data in enabled_students:
            try:
                dni = student_data.get("dni")
                email = student_data.get("student_email_id").strip()
                if not dni or not email:
                    errors.append(f"Datos incompletos para estudiante: {student_data['name']}")
                    continue

                # Verificar si el usuario ya existe en Moodle
                check_user_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "core_user_get_users",
                    "moodlewsrestformat": "json",
                    "criteria[0][key]": "username",
                    "criteria[0][value]": dni.lower()
                }
                response = requests.get(api_url, params=check_user_params)
                response_data = response.json()

                if response_data.get("users"):
                    # Usuario ya existe en Moodle, omitir
                    log_steps.append(f"Usuario existente en Moodle: {dni}")
                    continue
                else:
                    # Crear nuevo usuario
                    create_user_params = {
                        "wstoken": moodle_token,
                        "wsfunction": "core_user_create_users",
                        "moodlewsrestformat": "json",
                        "users[0][username]": dni.lower(),
                        "users[0][firstname]": student_data["first_name"],
                        "users[0][lastname]": student_data["last_name"],
                        "users[0][email]": email,
                        "users[0][idnumber]": dni.lower(),
                        "users[0][password]": dni.lower(),
                        "users[0][preferences][0][type]": "auth_forcepasswordchange",
                        "users[0][preferences][0][value]": "1"
                    }
                    create_response = requests.post(api_url, data=create_user_params)
                    create_response_data = create_response.json()
                    if create_response.status_code == 200 and isinstance(create_response_data, list):
                        user_id = create_response_data[0].get("id")
                        log_steps.append(f"Usuario creado en Moodle: {user_id}")
                        new_users.append({
                            "dni": dni,
                            "email": email,
                            "first_name": student_data["first_name"],
                            "last_name": student_data["last_name"],
                            "user_id": user_id
                        })
                    else:
                        errors.append(f"Error creando usuario: {dni}")
                        continue

            except Exception as e:
                errors.append(f"Error procesando estudiante {student_data['name']}: {str(e)}")
                continue

        # Asociar nuevos usuarios al curso y al grupo
        for user in new_users:
            try:
                # Inscribir al usuario en el curso
                enroll_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "enrol_manual_enrol_users",
                    "moodlewsrestformat": "json",
                    "enrolments[0][roleid]": 5,
                    "enrolments[0][userid]": user["user_id"],
                    "enrolments[0][courseid]": course_doc.moodle_course_code,
                }
                enroll_response = requests.post(api_url, data=enroll_params)
                if enroll_response.status_code == 200:
                    log_steps.append(f"Usuario vinculado al curso: {user['dni']}")
                else:
                    errors.append(f"Error vinculando usuario al curso: {user['dni']}")

                # Agregar al grupo
                if group_id:
                    add_to_group_params = {
                        "wstoken": moodle_token,
                        "wsfunction": "core_group_add_group_members",
                        "moodlewsrestformat": "json",
                        "members[0][groupid]": group_id,
                        "members[0][userid]": user["user_id"]
                    }
                    add_to_group_response = requests.post(api_url, data=add_to_group_params)
                    if add_to_group_response.status_code == 200:
                        log_steps.append(f"Usuario agregado al grupo: {user['dni']}")
                    else:
                        errors.append(f"Error agregando usuario {user['dni']} al grupo.")

            except Exception as e:
                errors.append(f"Error asociando usuario {user['dni']} al grupo: {str(e)}")

        # Enviar correos a nuevos usuarios
        for user in new_users:
            try:
                context = {
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "username": user["dni"].lower(),
                    "password": user["dni"].lower(),
                    "moodle_name": moodle_instance.site_name,
                    "moodle_url": moodle_url,
                }
                email_template = frappe.get_doc("Email Template", "alta_alumno_moodle")
                email_content = frappe.render_template(email_template.response, context)
                email_subject = frappe.render_template(email_template.subject, context)

                # Enviar correo
                frappe.sendmail(
                    recipients=[user["email"]],
                    sender="no_contestar@atumail.work",
                    subject=email_subject,
                    message=email_content
                )

                email_log.append(
                    f"Correo enviado a: {user['email']}\nAsunto: {email_subject}\n{'-'*50}"
                )
            except Exception as e:
                email_log.append(f"Error enviando correo a {user['email']}: {str(e)}")

        log_steps.append(f"Correos enviados a {len(new_users)} nuevos usuarios.")

    except Exception as e:
        errors.append(f"Error general: {str(e)}")

    # Registrar el log
    frappe.log_error("\n".join(log_steps), f"Sincronización del Curso: {course_name}")
    return {"status": "completado con errores" if errors else "completado", "errors": errors, "email_log": email_log}
