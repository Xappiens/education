import frappe
import re

# Tabla de letras según el resto de la división
LETRA_CONTROL = "TRWAGMYFPDXBNJZSQVHLCKE"

def calcular_letra_control(numero):
    """Calcula la letra de control basada en el número."""
    return LETRA_CONTROL[numero % 23]

def validar_dni(dni):
    """Valida un DNI nacional."""
    if not re.match(r'^\d{8}[A-Z]$', dni):
        return False  # Formato incorrecto
    numero = int(dni[:-1])
    letra = dni[-1]
    return calcular_letra_control(numero) == letra

def validar_nie(nie):
    """Valida un NIE extranjero."""
    if not re.match(r'^[XYZ]\d{7}[A-Z]$', nie):
        return False  # Formato incorrecto
    conversion = {'X': 0, 'Y': 1, 'Z': 2}
    numero = int(str(conversion[nie[0]]) + nie[1:-1])  # Convertir letra inicial
    letra = nie[-1]
    return calcular_letra_control(numero) == letra

def encontrar_duplicados_y_validar_dni():
    # Obtener todos los registros del Doctype 'Student'
    students = frappe.get_all(
        'Student',
        fields=['name', 'dni', 'student_email_id', 'first_name', 'last_name']
    )

    duplicados_dni = {}
    duplicados_email = {}
    duplicados_nombre_completo = {}
    invalid_dnis = []

    for student in students:
        # Validar campos nulos o vacíos
        dni = student.get('dni', '').strip() if student.get('dni') else ''
        email = student.get('student_email_id', '').strip() if student.get('student_email_id') else ''
        first_name = student.get('first_name', '').strip() if student.get('first_name') else ''
        last_name = student.get('last_name', '').strip() if student.get('last_name') else ''
        nombre_completo = f"{first_name} {last_name}".strip()

        # Validar DNI solo si no está vacío
        if dni:
            if not (validar_dni(dni) or validar_nie(dni)):
                invalid_dnis.append(f"- {student['name']} (DNI: {dni})")

        # Buscar duplicados por DNI
        if dni:
            if dni in duplicados_dni:
                duplicados_dni[dni].append(student['name'])
            else:
                duplicados_dni[dni] = [student['name']]

        # Buscar duplicados por correo electrónico
        if email:
            if email in duplicados_email:
                duplicados_email[email].append(student['name'])
            else:
                duplicados_email[email] = [student['name']]

        # Buscar duplicados por nombre completo
        if nombre_completo:
            if nombre_completo in duplicados_nombre_completo:
                duplicados_nombre_completo[nombre_completo].append(student['name'])
            else:
                duplicados_nombre_completo[nombre_completo] = [student['name']]

    # Filtrar solo duplicados
    duplicados_dni = {k: v for k, v in duplicados_dni.items() if len(v) > 1}
    duplicados_email = {k: v for k, v in duplicados_email.items() if len(v) > 1}
    duplicados_nombre_completo = {k: v for k, v in duplicados_nombre_completo.items() if len(v) > 1}

    # Crear un log ordenado
    log_mensajes = []

    # Agregar errores de DNI inválidos
    if invalid_dnis:
        log_mensajes.append("❌ **DNI Inválidos**:")
        log_mensajes.extend(invalid_dnis)

    # Agregar duplicados por DNI
    if duplicados_dni:
        log_mensajes.append("\n🔁 **Duplicados por DNI**:")
        for dni, names in duplicados_dni.items():
            log_mensajes.append(f"- DNI: {dni} ➡ {', '.join(names)}")

    # Agregar duplicados por correo electrónico
    if duplicados_email:
        log_mensajes.append("\n📧 **Duplicados por Correo Electrónico**:")
        for email, names in duplicados_email.items():
            log_mensajes.append(f"- Email: {email} ➡ {', '.join(names)}")

    # Agregar duplicados por nombre completo
    if duplicados_nombre_completo:
        log_mensajes.append("\n👤 **Duplicados por Nombre Completo**:")
        for nombre, names in duplicados_nombre_completo.items():
            log_mensajes.append(f"- Nombre: {nombre} ➡ {', '.join(names)}")

    # Registrar log en el sistema
    if log_mensajes:
        frappe.log_error(
            title="Reporte de Duplicados y Validaciones",
            message="\n".join(log_mensajes)
        )
