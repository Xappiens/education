import frappe

def renombrar_identificador_con_dni(batch_size=200, commit_interval=5):
    offset = 0
    lote_contador = 0

    # Contar el número de entradas al iniciar el proceso
    total_estudiantes = frappe.db.count("Student")

    while offset < total_estudiantes:
        # Obtener un lote de estudiantes ordenado por fecha de creación
        estudiantes = frappe.get_all(
            "Student", 
            fields=["name", "dni"], 
            limit=batch_size, 
            start=offset,
            order_by="creation ASC"  # Orden ascendente por fecha de creación
        )

        # Si no hay más estudiantes, termina el bucle
        if not estudiantes:
            break

        for estudiante in estudiantes:
            # Verificar que el DNI no esté vacío y que el identificador actual sea diferente al DNI
            if estudiante["dni"] and estudiante["name"] != estudiante["dni"]:
                try:
                    # Renombrar el documento de estudiante usando el DNI
                    frappe.rename_doc("Student", estudiante["name"], estudiante["dni"], force=True)
                except Exception:
                    # Si hay un error, continuar con el siguiente estudiante
                    pass

        # Incrementar el offset y el contador de lotes
        offset += batch_size
        lote_contador += 1

        # Confirmar los cambios cada `commit_interval` lotes
        if lote_contador % commit_interval == 0:
            frappe.db.commit()
    
    # Commit final por si quedan cambios pendientes
    frappe.db.commit()
