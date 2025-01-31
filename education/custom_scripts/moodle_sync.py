import frappe

#################################################################################
###################         SINCRONIZACIÓN DE CURSOS          ###################
#################################################################################

def sync_moodle_course(doc, method):
    # Simplificar la comprobación de clase virtual y código de Moodle
    doc.virtual_class = None if doc.virtual_class == "No" else doc.virtual_class

    if doc.moodle_course_code and doc.virtual_class:
        # Consolidar lógica de verificación y actualización o creación
        existing_moodle_course = frappe.db.exists("Moodle Course", {"course_code": doc.moodle_course_code})
        if existing_moodle_course:
            moodle_course_doc = frappe.get_doc("Moodle Course", existing_moodle_course)
            update_moodle_course(moodle_course_doc, doc)
        else:
            previous_moodle_course = frappe.get_all("Moodle Course", filters={"course_instance": doc.name}, fields=["name"])
            if previous_moodle_course:
                moodle_course_doc = frappe.get_doc("Moodle Course", previous_moodle_course[0].name)
                update_moodle_course(moodle_course_doc, doc)
            else:
                create_moodle_course(doc)
    else:
        delete_moodle_course_entry(doc, method)

def update_moodle_course(moodle_course_doc, doc):
    moodle_course_doc.course_name = doc.course_name
    moodle_course_doc.course_start_date = doc.start_date
    moodle_course_doc.course_end_date = doc.end_date
    moodle_course_doc.course_instance = doc.virtual_class
    moodle_course_doc.save()
    frappe.db.commit()

def create_moodle_course(doc):
    new_moodle_course_doc = frappe.get_doc({
        "doctype": "Moodle Course",
        "course_name": doc.course_name,
        "course_code": doc.moodle_course_code,
        "course_start_date": doc.start_date,
        "course_end_date": doc.end_date,
        "course_instance": doc.virtual_class
    })
    new_moodle_course_doc.insert()
    frappe.db.commit()

def delete_moodle_course_entry(doc, method):
    if doc.moodle_course_code:
        existing_moodle_course = frappe.db.exists("Moodle Course", {"course_code": doc.moodle_course_code})
        if existing_moodle_course:
            frappe.delete_doc("Moodle Course", existing_moodle_course)
            frappe.db.commit()

############################################################################################
#################    SINCRONIZACIÓN DE ESTUDIANTES A USUARIOS MOODLE   ######################
#############################################################################################

def sync_students_to_moodle_users(doc, method):
    student_ids = [entry.estudiante for entry in doc.custom_estudiantes if entry.estudiante]
    if not student_ids:
        return

    enabled_students = frappe.get_all("Student", filters={"name": ["in", student_ids], "enabled": 1}, fields=["name", "first_name", "last_name", "dni", "student_mobile_number", "student_email_id", "date_of_birth"])
    existing_dni = {user.user_dni for user in frappe.get_all("Moodle User", filters={"user_dni": ["in", [s.dni for s in enabled_students]]}, fields=["user_dni"])}

    for student_data in enabled_students:
        if student_data.dni not in existing_dni:
            create_moodle_user(student_data, "Student")

############################################################################################
###################   SINCRONIZACIÓN DE INSTRUCTORES A USUARIOS MOODLE  ####################
############################################################################################

def sync_instructors_to_moodle_users(doc, method):
    instructor_ids = [entry.instructor for entry in doc.custom_instructor if entry.instructor]
    if not instructor_ids:
        return

    enabled_instructors = frappe.get_all("Instructor", filters={"name": ["in", instructor_ids], "employee": ["!=", ""]}, fields=["name", "employee"])
    employee_ids = [inst.employee for inst in enabled_instructors]
    employee_data = frappe.get_all("Employee", filters={"name": ["in", employee_ids]}, fields=["name", "first_name", "last_name", "custom_dninie", "date_of_birth", "cell_number", "employee_email"])

    employee_map = {emp.name: emp for emp in employee_data}
    existing_dni = {user.user_dni for user in frappe.get_all("Moodle User", filters={"user_dni": ["in", [emp.custom_dninie for emp in employee_data]]}, fields=["user_dni"])}

    for instructor in enabled_instructors:
        employee = employee_map.get(instructor.employee)
        if employee and employee.custom_dninie not in existing_dni:
            create_moodle_user(employee, "Teacher")

############################################################################################
###################      CREACIÓN DE USUARIOS MOODLE AUXILIAR       ########################
############################################################################################

def create_moodle_user(user_data, role):
    moodle_user = frappe.get_doc({
        "doctype": "Moodle User",
        "user_name": user_data.first_name,
        "user_surname": user_data.last_name,
        "user_dni": user_data.dni,
        "user_phone": getattr(user_data, 'student_mobile_number', getattr(user_data, 'cell_number', None)),
        "user_email": getattr(user_data, 'student_email_id', getattr(user_data, 'employee_email', None)),
        "user_birthdate": user_data.date_of_birth,
        "user_role": role,
        "user_id": user_data.dni
    })
    moodle_user.insert(ignore_permissions=True)
    frappe.db.commit()
