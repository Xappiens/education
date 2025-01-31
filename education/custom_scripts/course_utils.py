import frappe

def before_delete_course(doc, method):
    # Buscar y eliminar la relación del curso en el Doctype Program (Expedientes)
    program_links = frappe.get_all('Program Course Link', filters={'course': doc.name})
    for link in program_links:
        frappe.db.delete('Program Course Link', {'name': link.name})



#################################################################################
###################       SINCRONIZACIÓN GRUPOS Y CURSO       ###################
#################################################################################

async def remove_group_students_from_course(doc, method):
    # Obtener el curso y el grupo que fue eliminado
    course_id = doc.parent  # ID del curso
    group_id = doc.grupo    # ID del grupo eliminado

    # Obtener lista de estudiantes en el grupo eliminado
    group_students = await frappe.get_all("Estudiantes Grupo Estudiantes", filters={"parent": group_id}, fields=["student"])
    group_student_ids = {student["student"] for student in group_students}

    # Obtener el curso y los estudiantes actuales
    course_doc = await frappe.get_doc("Course", course_id)
    existing_course_students = {entry.estudiante: entry for entry in course_doc.estudiantes_curso}

    # Eliminar estudiantes del grupo solo si no están en otros grupos del mismo curso
    for student_id in group_student_ids:
        # Verificar si el estudiante está en otros grupos del mismo curso
        other_groups = await frappe.get_all(
            "Grupo Estudiantes Curso",
            filters={"parent": course_id, "grupo": ["!=", group_id]},
            fields=["grupo"]
        )
        
        is_in_other_groups = False
        for other_group in other_groups:
            # Comprobar si el estudiante está en alguno de los otros grupos del curso
            other_group_students = await frappe.get_all("Estudiantes Grupo Estudiantes", filters={"parent": other_group["grupo"], "student": student_id})
            if other_group_students:
                is_in_other_groups = True
                break
        
        # Si el estudiante no está en otros grupos, eliminarlo del curso
        if not is_in_other_groups and student_id in existing_course_students:
            course_doc.remove(existing_course_students[student_id])

    # Ajustar group_roll_number después de eliminar
    for idx, entry in enumerate(course_doc.estudiantes_curso):
        entry.group_roll_number = idx + 1  # Reasignar números de orden de manera continua

    # Guardar los cambios en el curso
    await course_doc.save()



#################################################################################
###################  UTLIDAD LIMITE VISIBILIDAD INSTRUCTORES  ###################
#################################################################################

@frappe.whitelist()
def get_courses_for_instructor():
    """Obtiene los cursos asociados al instructor vinculado al usuario actual."""
    user_email = frappe.session.user

    # Paso 1: Buscar el registro del Instructor basado en el correo del usuario
    instructor = frappe.get_value("Instructor", {"mail": user_email}, "name")
    
  

    # Paso 2: Buscar los registros de 'Instructor Curso' asociados al Instructor
    instructor_courses = frappe.get_all(
        "Instructor Curso",
        filters={"instructor": instructor},
        fields=["parent"]  # 'parent' enlaza con el Doctype 'Course'
    )

    if not instructor_courses:
        return []

    # Paso 3: Obtener los nombres de los cursos
    course_ids = [course["parent"] for course in instructor_courses]

    # Paso 4: Retornar los cursos
    return frappe.get_all(
        "Course",
        filters={"name": ["in", course_ids]},
        fields=["name", "course_name"]
    )
