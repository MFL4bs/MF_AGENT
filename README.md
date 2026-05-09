# Sistema Inteligente de Chat para Leads

Sistema automatizado que:
- ✅ Califica leads con scoring inteligente
- ✅ Responde 24/7 usando manuales de empresa (RAG)
- ✅ Agenda citas en Google Calendar automáticamente
- ✅ Transfiere a humanos en casos complejos

## Configuración

### 1. AWS Setup
```bash
# Crear bucket S3 y subir manuales
aws s3 mb s3://mi-empresa-manuales
aws s3 cp ./manuales/ s3://mi-empresa-manuales/ --recursive

# Crear tabla DynamoDB
aws dynamodb create-table \
  --table-name mf_agent_sessions \
  --attribute-definitions AttributeName=phone,AttributeType=S \
  --key-schema AttributeName=phone,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 2. Google Calendar
1. Crear proyecto en Google Cloud Console
2. Habilitar Google Calendar API
3. Crear Service Account y descargar `google_credentials.json`
4. Compartir calendario con el email del Service Account

### 3. Twilio WhatsApp
1. Crear cuenta en Twilio
2. Configurar WhatsApp Sandbox o número productivo
3. Configurar webhook: `https://tu-dominio.com/webhook/whatsapp`

### 4. Variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 5. Instalar y ejecutar
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Despliegue en AWS

```bash
# Opción 1: AWS Lambda + API Gateway (serverless)
# Opción 2: ECS Fargate
# Opción 3: EC2 con Docker
```

## Flujo de conversación

1. Usuario envía mensaje → Calificación de lead
2. Si menciona keywords complejos → Transferencia a humano
3. Si solicita agendar → Extrae fecha/hora → Google Calendar
4. Preguntas generales → RAG sobre manuales → Respuesta automática

## Personalización

- **Scoring**: Editar `agent/lead_qualifier.py` → `QUALIFY_PROMPT`
- **Keywords complejos**: Modificar `COMPLEX_KEYWORDS` en `.env`
- **Manuales**: Cada perfil tiene su carpeta `data/{profile_id}/manuales/` con archivos .txt que el bot usa como referencia
  - Gestiona manuales desde la interfaz: Sidebar → 📚 Gestionar Manuales
  - Agrega información sobre tu empresa, productos, políticas, FAQ, etc.
  - Los cambios se aplican inmediatamente sin reiniciar
