import re
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
import frappe

def get_site_config():
    # Obtener la configuración desde el site_config.json
    config = frappe.get_site_config()
    return config

def connect_to_sharepoint_with_token(site_url):
    try:
        # Leer la configuración desde site_config.json
        site_config = frappe.get_site_config()
        id_cliente = site_config.get('id_sp_client')
        cert_finger = site_config.get('cert_finger')
        cert_path = site_config.get('cert_path')
        tenant_id = site_config.get('tenant_sp')

        # Configurar el contexto de cliente con el certificado
        ctx = ClientContext(site_url).with_client_certificate(
            client_id=id_cliente,
            thumbprint=cert_finger.replace(":", "").upper(),
            cert_path=cert_path,
            tenant=tenant_id
        )
        
        # Probar la conexión accediendo a algún recurso básico
        web = ctx.web.get().execute_query()
        return ctx
    except Exception as e:
        frappe.throw(f"Error al conectar a SharePoint con certificado: {str(e)}")

def sanitize_folder_name(name):
    # Reemplazar caracteres no permitidos por SharePoint ("/", "\", "*", etc.)
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '-', name)
    return sanitized_name

def create_sharepoint_folder(doc, method):
    # Obtener la configuración desde el archivo site_config.json
    config = get_site_config()
    user_email = config.get('user_sp')
    user_password = config.get('pass_sp')
    
    # URL del sitio de SharePoint
    site_url = "https://grupoatu365.sharepoint.com/sites/CENTROSCOLABORADORES-CentrosdeFormacin"
    folder_base_path = "/sites/CENTROSCOLABORADORES-CentrosdeFormacin/Shared Documents/Centros de Formación"
    
    # Limpiar el nombre de la carpeta para que no tenga caracteres no permitidos
    sanitized_room_number = sanitize_folder_name(doc.room_number)
    sanitized_room_name = sanitize_folder_name(doc.room_name)
    
    # Formar el nombre de la carpeta usando el room_number y room_name sanitizados
    folder_name = f"{sanitized_room_number} - {sanitized_room_name}"
    
    # Conectar a SharePoint usando UserCredential
    ctx = connect_to_sharepoint_with_token(site_url)
    
    # Construir la URL relativa para la carpeta en SharePoint
    folder_url = f"{folder_base_path}/{folder_name}"
    
    # Comprobar si la carpeta ya existe
    try:
        folder = ctx.web.get_folder_by_server_relative_url(folder_url)
        ctx.load(folder)
        ctx.execute_query()
        frappe.msgprint("La carpeta ya existe en SharePoint, se usará la carpeta existente.")
    except Exception:
        try:
            # Si la carpeta no existe, se intenta crear
            target_folder = ctx.web.folders.add(folder_url)
            ctx.execute_query()
            frappe.msgprint("Carpeta creada exitosamente en SharePoint.")
        except Exception as e:
            frappe.throw(f"Error al crear la carpeta en SharePoint: {str(e)}")
