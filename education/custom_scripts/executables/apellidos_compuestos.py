import frappe

def listar_apellidos_compuestos():
    # Diccionario de prefijos de apellidos compuestos
    prefijos = {
        "de", "del", "de la", "de las", "de los", "de san", "de santa",
        "la", "las", "los", "san", "santa", "delos", "delas", "da", "do", "das", "dos"
    }

    # Obtener todos los estudiantes
    estudiantes = frappe.get_all("Student", fields=["name", "last_name"])
    resultados = []

    for estudiante in estudiantes:
        last_name = estudiante.get("last_name", "")
        if not last_name:
            continue

        palabras = last_name.lower().split()
        primer_apellido = []
        segundo_apellido = []
        procesando_primer_apellido = True

        for i, palabra in enumerate(palabras):
            # Construir prefijos compuestos para primer apellido
            if procesando_primer_apellido:
                if i < len(palabras) - 1:
                    posible_prefijo = " ".join(palabras[:i + 1])
                    if posible_prefijo in prefijos:
                        primer_apellido.append(palabra)
                        continue
                
                primer_apellido.append(palabra)
                procesando_primer_apellido = False
            else:
                segundo_apellido.append(palabra)

        # Si el segundo apellido también es compuesto
        segundo_apellido_compuesto = []
        for i, palabra in enumerate(segundo_apellido):
            posible_prefijo = " ".join(segundo_apellido[:i + 1])
            if posible_prefijo in prefijos:
                segundo_apellido_compuesto.append(palabra)
            else:
                segundo_apellido_compuesto.extend(segundo_apellido[i:])
                break

        segundo_apellido = segundo_apellido_compuesto

        # Formatear apellidos
        primer_apellido = " ".join(primer_apellido).title()
        segundo_apellido = " ".join(segundo_apellido).title()

        resultados.append({
            "name": estudiante.get("name"),
            "last_name": last_name,
            "primer_apellido": primer_apellido,
            "segundo_apellido": segundo_apellido
        })

    # Generar mensaje único en el Error Log
    cuerpo = "Resultados de la Separación de Apellidos:\n\n"
    for resultado in resultados:
        cuerpo += (
            f"Estudiante: {resultado['name']}\n"
            f"Apellido Completo: {resultado['last_name']}\n"
            f"Primer Apellido: {resultado['primer_apellido']}\n"
            f"Segundo Apellido: {resultado['segundo_apellido']}\n\n"
        )

    frappe.log_error(message=cuerpo, title="Separación de Apellidos Compuestos")

    return "Proceso completado. Revisa el Error Log para los resultados."
