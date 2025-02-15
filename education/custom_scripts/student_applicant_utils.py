'''import frappe

def sync_student_applicants(doc, method):
    # Verificar si el estado del Student Applicant es "Approved" o "Admitted"
     if doc.application_status == 'Approved':
        # Comprobar si ya existe un estudiante con el mismo DNI en Student
        existing_student_id = frappe.get_value('Student', {'dni': doc.dni}, 'name')

        if not existing_student_id:
            # Crear el estudiante si no existe
            new_student = frappe.get_doc({
                'doctype': 'Student',
                'first_name': doc.first_name,
                'last_name': doc.last_name,
                'dni': doc.dni,
                'date_of_birth': doc.date_of_birth,
                'gender': doc.gender,
                'student_email_id': doc.student_email_id,
                'student_mobile_number': doc.student_mobile_number,
                'address_line_1': doc.address_line_1,
                'city': doc.city,
                'postcode': doc.pincode,
                'state': doc.state,
                'country': doc.country,
                'custom_situation': doc.employment_situation,
                'joining_date': frappe.utils.today(),
                'enabled': 1
            })
            new_student.insert(ignore_permissions=True)
            frappe.db.commit()
            student_id = new_student.name
        else:
            # Si el estudiante ya existe, usa el ID existente
            student_id = existing_student_id

        # Comprobar si ya existe una relación Student-Course en "Estudiantes y Acciones"
        existing_relation = frappe.get_value(
            'Estudiantes y Acciones',
            {'student_link': student_id, 'course_link': doc.course},
            'name'
        )

        if not existing_relation:
            # Crear la relación solo si no existe
            estudiantes_y_acciones = frappe.get_doc({
                'doctype': 'Estudiantes y Acciones',
                'student_link': student_id,
                'course_link': doc.course,
                'relation_date': frappe.utils.today()  # Fecha de creación de la relación
            })
            estudiantes_y_acciones.insert(ignore_permissions=True)
            frappe.db.commit()
'''