import frappe

def get_approved_applicants_missing_in_students():
    # Obtener las solicitudes de estudiantes aprobados
    approved_applicants = frappe.get_all(
        "Student Applicant",
        filters={"application_status": "Approved"},
        fields=["name", "dni"]
    )

    # Obtener todos los estudiantes (Student) y sus DNIs
    students = frappe.get_all("Student", fields=["dni"])
    student_dni_set = {student["dni"] for student in students}

    # Filtrar las solicitudes aprobadas cuyo DNI no esté en Student
    missing_in_students = [
        applicant for applicant in approved_applicants
        if applicant["dni"] not in student_dni_set
    ]

    # Limitar los resultados a las primeras 50
    missing_in_students = missing_in_students[:50]

    # Imprimir resultados
    print("=== Primeras 50 solicitudes aprobadas sin entrada en 'Student' ===")
    for applicant in missing_in_students:
        print(f"Solicitante: {applicant['name']}, DNI: {applicant['dni']}")

    # Imprimir el total
    total_missing = len(missing_in_students)
    print(f"\nTotal de solicitantes sin entrada en 'Student': {total_missing}")