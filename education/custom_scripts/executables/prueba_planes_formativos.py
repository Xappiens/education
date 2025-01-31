import frappe
from datetime import datetime

def prueba_actualizacion_planes_formativos():
    # Obtener el año actual en formato de dos dígitos
    year = datetime.now().year % 100  # Ejemplo: 2023 -> 23
    year_str = str(year).zfill(2)
    
    # Inicializar una lista para almacenar los detalles de cada entrada procesada
    log_data = []

    # Recorrer todas las entradas en "Planes Formativos"
    planes_formativos = frappe.get_all("Planes Formativos", fields=["name", "cat_plan", "tipo_de_plan", "abreviatura_categoria", "numero_incremento", "year"])

    for plan in planes_formativos:
        # Paso 1: Valores actuales antes de los cambios
        original_data = {
            "name": plan.name,
            "cat_plan": plan.cat_plan,
            "tipo_de_plan": plan.tipo_de_plan,
            "abreviatura_categoria": plan.abreviatura_categoria,
            "numero_incremento": plan.numero_incremento,
            "year": plan.year
        }

        # Paso 2: Obtener abreviatura y plan_type del Doctype "Planes" correspondiente
        plan_data = frappe.db.get_value("Planes", plan.cat_plan, ["abreviatura", "plan_type"], as_dict=True)
        if not plan_data:
            log_data.append({
                "name": plan.name,
                "error": f"No se encontró el Plan asociado con la categoría: {plan.cat_plan}"
            })
            continue

        # Simular los valores después de la actualización
        nuevo_abreviatura_categoria = plan_data.abreviatura
        nuevo_tipo_de_plan = plan_data.plan_type
        nuevo_year = year_str

        # Calcular numero_incremento simulado
        if not plan.numero_incremento:
            ultimo_incremento = frappe.db.get_value("Planes Formativos", {
                "tipo_de_plan": plan_data.plan_type,
                "abreviatura_categoria": plan_data.abreviatura,
                "year": year_str
            }, ["numero_incremento"], order_by="numero_incremento desc") or 0
            nuevo_incremento = int(ultimo_incremento) + 1
            numero_incremento = str(nuevo_incremento).zfill(2)
        else:
            numero_incremento = str(plan.numero_incremento).zfill(2)

        # Formato del nuevo nombre
        nuevo_nombre = f"PL-{nuevo_tipo_de_plan}-{nuevo_abreviatura_categoria}-{nuevo_year}-{numero_incremento}"

        # Almacenar los datos antes y después para esta entrada
        log_data.append({
            "name": plan.name,
            "original_data": original_data,
            "simulated_data": {
                "tipo_de_plan": nuevo_tipo_de_plan,
                "abreviatura_categoria": nuevo_abreviatura_categoria,
                "year": nuevo_year,
                "numero_incremento": numero_incremento,
                "nuevo_nombre": nuevo_nombre
            }
        })

    # Registrar toda la información recopilada en un solo log
    frappe.log_error(message=f"Datos completos: {log_data}", title="Prueba de Actualización de Planes")

