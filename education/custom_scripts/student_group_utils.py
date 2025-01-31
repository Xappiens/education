import frappe

async def update_course_students(doc, method):
    # Obtener los cursos asociados al grupo de estudiantes
    course_links = await frappe.get_all("Grupo Estudiantes Curso", filters={"grupo": doc.name}, fields=["parent"])
    
    # Obtener la lista de estudiantes actualizada del grupo
    group_students = await frappe.get_all("Estudiantes Grupo Estudiantes", filters={"parent": doc.name}, fields=["student"])
    group_student_ids = {student["student"] for student in group_students}
    
    for course_link in course_links:
        # Obtener el curso y los estudiantes existentes en la tabla 'Estudiantes Curso'
        course_doc = await frappe.get_doc("Course", course_link["parent"])
        existing_course_students = {entry.estudiante: entry for entry in course_doc.estudiantes_curso}
        
        # 1. Agregar estudiantes que están en el grupo pero no en el curso
        for student_id in group_student_ids:
            if student_id not in existing_course_students:
                new_entry = course_doc.append("estudiantes_curso", {"estudiante": student_id})
                # Asegurarse de que 'group_roll_number' se inicialice
                if not hasattr(new_entry, 'group_roll_number'):
                    new_entry.group_roll_number = len(existing_course_students) + 1  # Asignar un nuevo número de orden

        # 2. Eliminar estudiantes que ya no están en el grupo pero están en el curso
        for student_id, entry in existing_course_students.items():
            if student_id not in group_student_ids:
                # Verificar si el estudiante está en otro grupo del mismo curso
                other_groups = await frappe.get_all(
                    "Grupo Estudiantes Curso", 
                    filters={"parent": course_link["parent"], "grupo": ["!=", doc.name]},
                    fields=["grupo"]
                )
                
                is_in_other_groups = False
                for group in other_groups:
                    # Comprobar si el estudiante está en alguno de los otros grupos del curso
                    group_students = await frappe.get_all("Estudiantes Grupo Estudiantes", filters={"parent": group["grupo"], "student": student_id})
                    if group_students:
                        is_in_other_groups = True
                        break
                
                # Si el estudiante no está en otros grupos, eliminarlo del curso
                if not is_in_other_groups:
                    course_doc.remove(entry)
        
        # Guardar los cambios en el curso
        await course_doc.save()
