import frappe
import requests
import json
from datetime import datetime, time as dt_time
import pytz
from frappe import _

@frappe.whitelist()
def sync_selected_students(row_numbers, course_name):
    """
    Sincroniza estudiantes seleccionados en la tabla de un curso con Moodle.
    Devuelve el log completo y sin filtrar al cliente.
    """
    log_steps = []
    errors = []

    try:
        row_numbers = json.loads(row_numbers)
        if not row_numbers:
            return {"status": "Error", "log": ["No hay estudiantes seleccionados."]}

        course_doc = frappe.get_doc("Course", course_name)
        log_steps.append(f"Curso obtenido: {course_doc.name}")

        selected_rows = [row for row in course_doc.custom_estudiantes if row.idx in row_numbers]
        if not selected_rows:
            return {"status": "Error", "log": ["No se encontraron filas seleccionadas."]}

        selected_students = [row.estudiante for row in selected_rows]
        log_steps.append(f"Estudiantes seleccionados: {', '.join(selected_students)}")

        enabled_students = frappe.get_all(
            "Student",
            filters={"name": ["in", selected_students], "enabled": 1},
            fields=["name", "first_name", "last_name", "dni", "student_email_id", "student_mobile_number"]
        )
        if not enabled_students:
            log_steps.append("No se encontraron estudiantes habilitados para sincronizar.")
            return {"status": "Error", "log": log_steps}

        log_steps.append("Estudiantes habilitados para sincronización:")
        for student in enabled_students:
            log_steps.append(f"{student}")

        moodle_instance = frappe.get_doc("Moodle Instance", course_doc.virtual_class)
        moodle_url = f"https://{moodle_instance.site_url}" if not moodle_instance.site_url.startswith("http") else moodle_instance.site_url
        api_url = f"{moodle_url}/webservice/rest/server.php"
        moodle_token = moodle_instance.api_key

        group_name = f"{course_doc.expediente}_{course_doc.code}_{course_doc.group}"
        group_id = None

        group_params = {
            "wstoken": moodle_token,
            "wsfunction": "core_group_get_course_groups",
            "moodlewsrestformat": "json",
            "courseid": course_doc.moodle_course_code,
        }
        group_response = requests.get(api_url, params=group_params)
        group_data = group_response.json()

        log_steps.append(f"Respuesta de grupos en Moodle: {group_data}")

        if isinstance(group_data, list):
            for group in group_data:
                if group["name"] == group_name:
                    group_id = group["id"]
                    log_steps.append(f"Grupo existente en Moodle: {group_name} (ID: {group_id})")
                    break

        if not group_id:
            create_group_params = {
                "wstoken": moodle_token,
                "wsfunction": "core_group_create_groups",
                "moodlewsrestformat": "json",
                "groups[0][name]": group_name,
                "groups[0][courseid]": course_doc.moodle_course_code,
                "groups[0][description]": f"Grupo para el curso {course_doc.name}",
            }
            create_group_response = requests.post(api_url, data=create_group_params)
            create_group_data = create_group_response.json()
            log_steps.append(f"Respuesta al crear grupo en Moodle: {create_group_data}")

            if isinstance(create_group_data, list) and create_group_data[0].get("id"):
                group_id = create_group_data[0]["id"]
            else:
                log_steps.append("Error al crear el grupo en Moodle.")
                frappe.log_error("\n".join(log_steps), "Sincronización de Estudiantes")
                return {"status": "Error", "log": log_steps}

        timezone = pytz.timezone("Europe/Madrid")
        start_date = timezone.localize(datetime.combine(course_doc.start_date, dt_time.min))
        end_date = timezone.localize(datetime.combine(course_doc.end_date, dt_time.max))
        timestart = int(start_date.timestamp())
        timeend = int(end_date.timestamp())

        for student in enabled_students:
            try:
                dni = student.get("dni")
                email = student.get("student_email_id").strip()
                if not dni or not email:
                    errors.append(f"Estudiante {student['name']} no tiene DNI o correo electrónico.")
                    continue

                log_steps.append(f"Procesando estudiante {dni}: {student['first_name']} {student['last_name']}")

                check_user_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "core_user_get_users",
                    "moodlewsrestformat": "json",
                    "criteria[0][key]": "username",
                    "criteria[0][value]": dni.lower(),
                }
                user_response = requests.get(api_url, params=check_user_params)
                user_data = user_response.json()
                log_steps.append(f"Respuesta al buscar usuario en Moodle: {user_data}")

                user_id = None
                if user_data.get("users"):
                    user_id = user_data["users"][0]["id"]

                    # Actualizar teléfono y correo si ya existe
                    update_user_params = {
                        "wstoken": moodle_token,
                        "wsfunction": "core_user_update_users",
                        "moodlewsrestformat": "json",
                        "users[0][id]": user_id,
                        "users[0][email]": email,
                        "users[0][phone1]": student.get("student_mobile_number", ""),
                        "users[0][preferences][0][type]": "auth_forcepasswordchange",
                        "users[0][preferences][0][value]": "1",
                    }
                    update_user_response = requests.post(api_url, data=update_user_params)
                    update_user_data = update_user_response.json()
                    log_steps.append(f"Usuario existente actualizado: {update_user_data}")

                else:
                    create_user_params = {
                        "wstoken": moodle_token,
                        "wsfunction": "core_user_create_users",
                        "moodlewsrestformat": "json",
                        "users[0][username]": dni.lower(),
                        "users[0][firstname]": student["first_name"],
                        "users[0][lastname]": student["last_name"],
                        "users[0][email]": email,
                        "users[0][idnumber]": dni.lower(),
                        "users[0][password]": dni.lower(),
                        "users[0][phone1]": student.get("student_mobile_number", ""),
                        "users[0][preferences][0][type]": "auth_forcepasswordchange",
                        "users[0][preferences][0][value]": "1",
                    }
                    create_user_response = requests.post(api_url, data=create_user_params)
                    create_user_data = create_user_response.json()

                    log_steps.append(f"Respuesta al crear usuario: {create_user_data}")

                    if isinstance(create_user_data, list) and create_user_data[0].get("id"):
                        user_id = create_user_data[0]["id"]
                    else:
                        errors.append(f"Error al crear usuario {dni}: {create_user_data}")
                        continue

                enroll_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "enrol_manual_enrol_users",
                    "moodlewsrestformat": "json",
                    "enrolments[0][roleid]": 5,
                    "enrolments[0][userid]": user_id,
                    "enrolments[0][courseid]": course_doc.moodle_course_code,
                    "enrolments[0][timestart]": timestart,
                    "enrolments[0][timeend]": timeend,
                }
                requests.post(api_url, data=enroll_params)

                add_to_group_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "core_group_add_group_members",
                    "moodlewsrestformat": "json",
                    "members[0][groupid]": group_id,
                    "members[0][userid]": user_id
                }
                requests.post(api_url, data=add_to_group_params)

            except Exception as e:
                errors.append(f"Error procesando estudiante {student['name']}: {str(e)}")

        result_status = "Con errores" if errors else "Con éxito"
        frappe.log_error("\n".join(log_steps), f"Sincronización {result_status}")
        return {"status": f"Sincronización completada {result_status}", "log": log_steps, "errors": errors}

    except Exception as e:
        log_steps.append(f"Error general: {str(e)}")
        frappe.log_error("\n".join(log_steps), "Sync Students Fatal Error")
        return {"status": "Error", "log": log_steps}
