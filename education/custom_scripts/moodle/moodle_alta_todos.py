import requests
import pytz
import frappe
from frappe import _
from datetime import datetime, time as dt_time


@frappe.whitelist()
def sync_students_to_moodle(course_name):
    """
    Sincroniza estudiantes con Moodle, los agrega al curso y los incluye en el grupo especificado.
    - Verifica si el grupo ya existe antes de intentar crearlo.
    - Crea usuarios si no existen y los agrega al curso y grupo.
    """
    log_steps = []
    errors = []

    try:
        # Obtener el documento del curso
        course_doc = frappe.get_doc("Course", course_name)
        log_steps.append(f"Curso obtenido:\nNombre: {course_doc.name}\nCódigo Moodle: {course_doc.moodle_course_code}\nGrupo: {course_doc.group}")

        # Configuración de Moodle
        moodle_instance = frappe.get_doc("Moodle Instance", course_doc.virtual_class)
        moodle_url = moodle_instance.site_url
        if not moodle_url.startswith("http://") and not moodle_url.startswith("https://"):
            moodle_url = f"https://{moodle_url}"
        api_url = f"{moodle_url}/webservice/rest/server.php"
        moodle_token = moodle_instance.api_key
        log_steps.append(f"Instancia de Moodle configurada:\nNombre: {moodle_instance.site_name}\nURL: {moodle_url}")


        ########################################################################################################################


        # Generar nombre del grupo
        group_name = f"{course_doc.expediente}_{course_doc.code}_{course_doc.group}"

        # Verificar si el grupo ya existe en Moodle
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
                    log_steps.append(f"Grupo ya existente en Moodle:\nNombre: {group_name}\nID: {group_id}")
                    break

        # Crear el grupo solo si no existe
        if not group_id:
            try:
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

                if isinstance(create_group_data, list):
                    for group in create_group_data:
                        if group.get("id"):
                            group_id = group["id"]
                            log_steps.append(f"Grupo creado en Moodle:\nNombre: {group_name}\nID: {group_id}")
                            break

                elif "errorcode" in create_group_data and create_group_data["errorcode"] == "invalidparameter":
                    # Si Moodle indica que ya existe, loguearlo y continuar
                    log_steps.append(f"Grupo ya existe según Moodle, pero no fue detectado inicialmente:\n{create_group_data}")
                else:
                    log_steps.append(f"Error al crear el grupo en Moodle:\nRespuesta: {create_group_data}")
                    frappe.log_error("\n".join(log_steps), f"Error en Sincronización de Curso: {course_doc.name}")
                    return "Error al crear el grupo en Moodle."

            except Exception as group_creation_error:
                log_steps.append(f"Excepción al crear grupo: {str(group_creation_error)}")
                frappe.log_error("\n".join(log_steps), f"Error en Sincronización de Curso: {course_doc.name}")
                return "Error crítico al intentar crear el grupo en Moodle."


        ########################################################################################################################


        # Obtener estudiantes habilitados
        student_ids = [entry.estudiante for entry in course_doc.custom_estudiantes if entry.estudiante]
        enabled_students = frappe.get_all(
            "Student",
            filters={"name": ["in", student_ids], "enabled": 1},
            fields=["name", "first_name", "last_name", "dni", "student_mobile_number", "student_email_id"]
        )
        log_steps.append(f"Estudiantes habilitados:\n{enabled_students}")

        # Procesar estudiantes
        for student_data in enabled_students:
            try:
                dni = student_data.get("dni")
                if not dni:
                    errors.append(f"Estudiante {student_data['name']} no tiene DNI.")
                    continue

                email = student_data.get("student_email_id").strip()
                if not email:
                    errors.append(f"Estudiante {student_data['name']} no tiene correo electrónico.")
                    continue

                log_steps.append(f"Procesando estudiante {dni} - {student_data['first_name']} {student_data['last_name']}")

                # Verificar si el usuario ya existe en Moodle
                check_user_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "core_user_get_users",
                    "moodlewsrestformat": "json",
                    "criteria[0][key]": "username",
                    "criteria[0][value]": dni.lower()  # El DNI como username
                }
                response = requests.get(api_url, params=check_user_params)
                response_data = response.json()

                if response_data.get("users"):
                    user_id = response_data["users"][0]["id"]
                    log_steps.append(f"Usuario ya existente en Moodle:\nID Moodle: {user_id}")

                    # Actualizar la contraseña del usuario existente
                    if dni:
                        update_user_params = {
                            "wstoken": moodle_token,
                            "wsfunction": "core_user_update_users",
                            "moodlewsrestformat": "json",
                            "users[0][id]": user_id,
                            "users[0][password]": dni.lower(),  # Actualizar la contraseña al DNI (con la letra en minúscula)
                            "users[0][preferences][0][type]": "auth_forcepasswordchange",  # Forzar cambio de contraseña
                            "users[0][preferences][0][value]": "1"
                        }
                        try:
                            update_response = requests.post(api_url, data=update_user_params)
                            update_response_data = update_response.json()
                            if update_response.status_code == 200:
                                log_steps.append(f"Contraseña actualizada y forzado cambio de contraseña para usuario existente:\nDNI: {dni}")
                            else:
                                log_steps.append(f"Error al actualizar contraseña y forzar cambio:\n{update_response_data}")
                        except Exception as e:
                            log_steps.append(f"Excepción al actualizar usuario existente (DNI: {dni}): {str(e)}")
                else:
                    # Crear nuevo usuario con contraseña obligatoria
                    create_user_params = {
                        "wstoken": moodle_token,
                        "wsfunction": "core_user_create_users",
                        "moodlewsrestformat": "json",
                        "users[0][username]": dni.lower(),
                        "users[0][firstname]": student_data["first_name"],
                        "users[0][lastname]": student_data["last_name"],
                        "users[0][email]": email,
                        "users[0][phone1]": student_data["student_mobile_number"],
                        "users[0][idnumber]": dni.lower(),
                        "users[0][password]": dni.lower(),  # Contraseña inicial igual al DNI
                        "users[0][preferences][0][type]": "auth_forcepasswordchange",  # Forzar cambio de contraseña
                        "users[0][preferences][0][value]": "1"
                    }
                    create_response = requests.post(api_url, data=create_user_params)
                    create_response_data = create_response.json()

                    if isinstance(create_response_data, list):
                        for user in create_response_data:
                            if user.get("id"):
                                user_id = user["id"]
                                log_steps.append(f"Usuario creado en Moodle:\nID Moodle: {user_id}")
                                
                                # Solicitar restablecimiento de contraseña
                                reset_password_params = {
                                    "wstoken": moodle_token,
                                    "wsfunction": "core_auth_request_password_reset",
                                    "moodlewsrestformat": "json",
                                    "username": dni.lower(),  # Usar el DNI como nombre de usuario
                                }
                                reset_response = requests.post(api_url, data=reset_password_params)
                                reset_response_data = reset_response.json()

                                if reset_response.status_code == 200:
                                    log_steps.append(f"Correo de restablecimiento de contraseña enviado a: {student_data['student_email_id']}")
                                else:
                                    log_steps.append(f"Error al enviar el correo de restablecimiento de contraseña:\n{reset_response_data}")
                            else:
                                log_steps.append(f"Error al crear usuario en Moodle: no se encontró un ID de usuario en la respuesta.\nDNI: {dni}\nRespuesta: {create_response_data}")
                    else:
                        log_steps.append(f"Error al crear usuario en Moodle: respuesta inesperada.\nDNI: {dni}\nRespuesta: {create_response_data}")

                # Definir la zona horaria
                timezone = pytz.timezone("Europe/Madrid")

                # Asegurarse de que las fechas incluyan horas
                start_date = timezone.localize(datetime.combine(course_doc.start_date, dt_time.min))
                end_date = timezone.localize(datetime.combine(course_doc.end_date, dt_time.max))

                timestart = int(start_date.timestamp())
                timeend = int(end_date.timestamp())

                # Vincular usuario al curso
                enroll_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "enrol_manual_enrol_users",
                    "moodlewsrestformat": "json",
                    "enrolments[0][roleid]": 5,  # ID de rol para estudiante
                    "enrolments[0][userid]": user_id,
                    "enrolments[0][courseid]": course_doc.moodle_course_code,
                    "enrolments[0][timestart]": timestart,
                    "enrolments[0][timeend]": timeend,
                }
                try:
                    enroll_response = requests.post(api_url, data=enroll_params)
                    enroll_response_data = enroll_response.json()

                    if enroll_response.status_code == 200:
                        log_steps.append(f"Usuario vinculado al curso:\nDNI: {dni}\nID Curso Moodle: {course_doc.moodle_course_code}")
                    else:
                        error_message = f"Error al vincular usuario al curso:\nDNI: {dni}\nRespuesta: {enroll_response_data}"
                        log_steps.append(error_message)
                        errors.append(error_message)
                except Exception as e:
                    error_message = f"Excepción al vincular usuario al curso (DNI: {dni}): {str(e)}"
                    log_steps.append(error_message)
                    errors.append(error_message)

                # Vincular usuario al grupo
                add_to_group_params = {
                    "wstoken": moodle_token,
                    "wsfunction": "core_group_add_group_members",
                    "moodlewsrestformat": "json",
                    "members[0][groupid]": group_id,  # ID del grupo
                    "members[0][userid]": user_id    # ID del usuario
                }
                try:
                    add_to_group_response = requests.post(api_url, data=add_to_group_params)
                    add_to_group_data = add_to_group_response.json()
                except Exception as e:
                    log_steps.append(f"Error al agregar usuario al grupo: {str(e)}")
                    continue

                if add_to_group_response.status_code == 200:
                    log_steps.append(f"Usuario agregado al grupo:\nDNI: {dni}\nGrupo: {course_doc.group}")
                else:
                    log_steps.append(f"Error al agregar usuario al grupo:\nDNI: {dni}\nRespuesta: {add_to_group_data}")

            except Exception as student_error:
                log_steps.append(f"Error al procesar estudiante {student_data['name']} (DNI: {dni}): {str(student_error)}")
                continue

        log_steps.append("Sincronización completada con éxito.")

    except Exception as e:
        error_message = f"Error general: {str(e)}"
        log_steps.append(error_message)
        errors.append(error_message)

    frappe.log_error("\n".join(log_steps), f"Sincronización de Curso: {course_doc.name}")

    if errors:
        frappe.msgprint(_("Se encontraron errores durante la sincronización:\n") + "\n".join(errors))

    if errors:
        result_log = {
            "status": "Sincronización completada con errores",
            "log": log_steps,
            "errors": errors
        }
    else:
        result_log = {
            "status": "Sincronización completada con éxito",
            "log": log_steps
        }

    return result_log

