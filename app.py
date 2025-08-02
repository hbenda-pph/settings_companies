import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from google.cloud import bigquery
from google.auth import default

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configuración de BigQuery
PROJECT_ID = 'platform-partners-qua'
DATASET_NAME = 'settings'  # Corregido: era 'platform_partners'
TABLE_NAME = 'companies'

def get_bigquery_client():
    """Obtiene el cliente de BigQuery"""
    try:
        print("🔍 Intentando crear cliente BigQuery...")
        credentials, project = default()
        print(f"✅ Credenciales obtenidas. Proyecto: {project}")
        client = bigquery.Client(credentials=credentials, project=project)
        print("✅ Cliente BigQuery creado exitosamente")
        return client
    except Exception as e:
        print(f"❌ Error al crear cliente BigQuery: {e}")
        return None

def get_companies():
    """Obtiene todas las compañías de la tabla companies"""
    print("🔄 Iniciando obtención de compañías...")
    client = get_bigquery_client()
    if not client:
        print("❌ No se pudo crear el cliente BigQuery")
        return []
    
    query = f"""
        SELECT 
            company_id,
            company_name,
            company_new_name,
            company_project_id,
            company_bigquery_status
        FROM `{PROJECT_ID}.{DATASET_NAME}.{TABLE_NAME}`
        ORDER BY company_name
    """
    
    print(f"📝 Ejecutando query: {query}")
    
    try:
        query_job = client.query(query)
        print("⏳ Query enviada, esperando resultados...")
        results = query_job.result()
        companies = []
        for row in results:
            companies.append({
                'company_id': row.company_id,
                'company_name': row.company_name,
                'company_new_name': row.company_new_name,
                'company_project_id': row.company_project_id,
                'company_bigquery_status': row.company_bigquery_status
            })
        print(f"✅ Se obtuvieron {len(companies)} compañías")
        return companies
    
    except Exception as e:
        print(f"❌ Error al obtener compañías: {e}")
        return []

def update_company_status(company_id, new_status):
    """Actualiza el status de una compañía"""
    client = get_bigquery_client()
    if not client:
        return False, "Error al conectar con BigQuery"
    
    query = f"""
        UPDATE `{PROJECT_ID}.{DATASET_NAME}.{TABLE_NAME}`
        SET company_bigquery_status = @new_status
        WHERE company_id = @company_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("new_status", "BOOLEAN", new_status),
            bigquery.ScalarQueryParameter("company_id", "INTEGER", company_id),
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()
        return True, "Status actualizado exitosamente"
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"

def update_all_companies_status(new_status):
    """Actualiza el status de todas las compañías"""
    client = get_bigquery_client()
    if not client:
        return False, "Error al conectar con BigQuery"
    
    query = f"""
        UPDATE `{PROJECT_ID}.{DATASET_NAME}.{TABLE_NAME}`
        SET company_bigquery_status = @new_status
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("new_status", "BOOLEAN", new_status),
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()
        return True, f"Status actualizado exitosamente para todas las compañías a: {new_status}"
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"

@app.route('/')
def index():
    """Página principal"""
    print("🏠 Accediendo a la página principal...")
    companies = get_companies()
    print(f"📊 Renderizando template con {len(companies)} compañías")
    return render_template('index.html', companies=companies)

@app.route('/api/companies')
def api_companies():
    """API para obtener compañías"""
    print("🔌 API /api/companies llamada")
    companies = get_companies()
    print(f"📤 Enviando {len(companies)} compañías via API")
    return jsonify(companies)

@app.route('/api/update_status', methods=['POST'])
def api_update_status():
    """API para actualizar el status de una compañía"""
    data = request.get_json()
    company_id = data.get('company_id')
    new_status = data.get('status')
    
    if company_id is None or new_status is None:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
    
    success, message = update_company_status(company_id, new_status)
    return jsonify({'success': success, 'message': message})

@app.route('/update_status', methods=['POST'])
def update_status():
    """Actualizar status desde formulario"""
    company_id = request.form.get('company_id')
    new_status = request.form.get('status') == 'true'
    
    if not company_id:
        flash('ID de compañía requerido', 'error')
        return redirect(url_for('index'))
    
    success, message = update_company_status(int(company_id), new_status)
    
    if success:
        flash('Status actualizado exitosamente', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/update_all_status', methods=['POST'])
def api_update_all_status():
    """API para actualizar el status de todas las compañías"""
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status is None:
        return jsonify({'success': False, 'message': 'Status requerido'}), 400
    
    success, message = update_all_companies_status(new_status)
    return jsonify({'success': success, 'message': message})

@app.route('/update_all_status', methods=['POST'])
def update_all_status():
    """Actualizar status de todas las compañías desde formulario"""
    new_status = request.form.get('status') == 'true'
    
    success, message = update_all_companies_status(new_status)
    
    if success:
        flash(f'Todas las compañías actualizadas: {message}', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('index'))

@app.route('/debug')
def debug_info():
    """Ruta de debug para verificar la configuración"""
    debug_info = {
        'project_id': PROJECT_ID,
        'dataset_name': DATASET_NAME,
        'table_name': TABLE_NAME,
        'bigquery_client': None,
        'credentials': None,
        'error': None
    }
    
    try:
        print("🔍 Verificando credenciales...")
        credentials, project = default()
        debug_info['credentials'] = {
            'project': project,
            'service_account_email': getattr(credentials, 'service_account_email', 'N/A'),
            'token': 'Disponible' if credentials.token else 'No disponible'
        }
        
        print("🔍 Verificando cliente BigQuery...")
        client = get_bigquery_client()
        if client:
            debug_info['bigquery_client'] = 'Conectado'
            
            # Verificar si la tabla existe
            try:
                table_ref = client.dataset(DATASET_NAME).table(TABLE_NAME)
                table = client.get_table(table_ref)
                debug_info['table_exists'] = True
                debug_info['table_schema'] = [field.name for field in table.schema]
            except Exception as e:
                debug_info['table_exists'] = False
                debug_info['table_error'] = str(e)
        else:
            debug_info['bigquery_client'] = 'Error de conexión'
            
    except Exception as e:
        debug_info['error'] = str(e)
        print(f"❌ Error en debug: {e}")
    
    return jsonify(debug_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True) 