# 🚗 SmartParking Flask - Visualización en Tiempo Real

Sistema de monitorización visual en tiempo real del estado de plazas de parking, conectado a MongoDB Atlas y procesado por Apache NiFi desde Apache Kafka.

## 📋 Características

- ✅ **Visualización en tiempo real** del estado de cada plaza (libre/ocupada)
- ✅ **Actualización automática** cada 5 segundos
- ✅ **Mapa visual interactivo** con colores (verde=libre, rojo=ocupada)
- ✅ **Filtros por nivel** (L1, L2, L3, etc.)
- ✅ **Estadísticas en vivo** (total, libres, ocupadas, % ocupación)
- ✅ **Tooltips informativos** con detalles de cada plaza (temperatura, batería, última actualización)
- ✅ **Diseño responsive** adaptado a móviles y tablets
- ✅ **Conexión a MongoDB Atlas** en la nube

## 🏗️ Arquitectura

```
Sensores IoT → Kafka → NiFi → MongoDB Atlas → Flask → Navegador
                                    ↓
                                  Dremio (Análisis)
```

## 📁 Estructura del Proyecto

```
SmartParking-Web/
├── app.py                  # Aplicación Flask principal
├── templates/
│   └── index.html         # Interfaz web visual
├── static/               # (Estilos en línea por ahora)
├── .env                  # Variables de entorno (CREAR)
├── requirements.txt      # Dependencias Python
├── smartparking.log     # Log de la aplicación (se genera)
└── README.md            # Este archivo
```

## 🚀 Instalación y Configuración

### Prerequisitos

- Python 3.10 o superior
- Cuenta en MongoDB Atlas (gratuita)
- Datos generados por NiFi desde Kafka (proyecto completo)

### Paso 1: Clonar/Crear el proyecto

```bash
# Crear directorio del proyecto
mkdir SmartParking-Web
cd SmartParking-Web

# Crear los archivos necesarios (app.py, templates/index.html, etc.)
```

### Paso 2: Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar MongoDB Atlas

1. **Crear cuenta en MongoDB Atlas** (si no la tienes):

   - Ve a https://www.mongodb.com/cloud/atlas/register
   - Regístrate gratuitamente

2. **Crear cluster** (si no lo tienes):

   - Selecciona FREE tier (M0)
   - Región: Europe (Madrid o Frankfurt)

3. **Configurar acceso**:

   - **Database Access**: Crear usuario con permisos de lectura/escritura
   - **Network Access**: Añadir IP `0.0.0.0/0` (para desarrollo)

4. **Obtener Connection String**:
   - Cluster → Connect → Drivers
   - Copiar la URI: `mongodb+srv://usuario:password@cluster.mongodb.net/...`

### Paso 5: Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# MongoDB Atlas
MONGO_URI=mongodb+srv://smartparking_user:TU_PASSWORD@smartparkingcluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGO_DB=smartparking

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=genera_una_clave_secreta_aleatoria
```

**⚠️ IMPORTANTE**: Reemplaza `TU_PASSWORD` con tu contraseña real de MongoDB Atlas

**Generar SECRET_KEY segura**:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Paso 6: Verificar conexión a MongoDB

Antes de ejecutar Flask, verifica la conexión:

```python
# test_connection.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('MONGO_URI')
client = MongoClient(uri)

try:
    client.admin.command('ping')
    print("✓ Conexión exitosa a MongoDB Atlas")

    db = client.smartparking
    bays_count = db.bays.count_documents({})
    events_count = db.events.count_documents({})

    print(f"✓ Plazas en BD: {bays_count}")
    print(f"✓ Eventos en BD: {events_count}")

except Exception as e:
    print(f"✗ Error: {e}")
```

```bash
python test_connection.py
```

## ▶️ Ejecutar la Aplicación

### Modo desarrollo

```bash
# Asegúrate de estar en el entorno virtual
python app.py
```

Verás algo como:

```
======================================================
🚀 Iniciando SmartParking Flask Application
======================================================
📊 Base de datos: smartparking
🌐 Servidor: http://0.0.0.0:5000
======================================================
✓ Conectado exitosamente a MongoDB Atlas
 * Running on http://0.0.0.0:5000
```

### Acceder a la aplicación

Abre tu navegador en:

- **Local**: http://localhost:5000
- **Desde otros dispositivos** en la misma red: http://TU_IP:5000

## 🔌 API Endpoints

La aplicación expone varios endpoints REST:

### GET `/`

Página principal con el mapa visual del parking

### GET `/api/health`

Health check del servicio

```json
{
  "status": "healthy",
  "database": "connected",
  "total_bays": 90,
  "total_events": 15234
}
```

### GET `/api/bays`

Obtener todas las plazas

```json
{
  "success": true,
  "count": 90,
  "data": [
    {
      "bay_id": "L1-A-001",
      "parking_id": "PK-CADIZ-01",
      "level": "L1",
      "occupied": false,
      "metrics": {
        "temperature_c": 23.4,
        "battery_pct": 78
      },
      "updated_at": "2025-10-20T10:15:30Z"
    }
  ]
}
```

### GET `/api/stats`

Estadísticas generales y por nivel

```json
{
  "success": true,
  "total": 90,
  "occupied": 45,
  "free": 45,
  "occupancy_rate": 50.0,
  "levels": [
    {
      "level": "L1",
      "total": 30,
      "occupied": 15,
      "free": 15,
      "occupancy_rate": 50.0,
      "avg_temperature": 23.2,
      "avg_battery": 75.5
    }
  ]
}
```

### GET `/api/bays/level/<level>`

Plazas de un nivel específico (L1, L2, L3...)

### GET `/api/maintenance/low-battery`

Plazas con batería baja que requieren mantenimiento

## 🎨 Características de la Interfaz

### Panel de Estadísticas

- Total de plazas
- Plazas libres (verde)
- Plazas ocupadas (rojo)
- Porcentaje de ocupación (azul)

### Filtros

- **Todos los niveles**: Vista completa
- **Nivel L1, L2, L3**: Vista filtrada por nivel

### Mapa de Plazas

- **Verde**: Plaza libre 🟢
- **Rojo**: Plaza ocupada 🔴
- **Hover**: Muestra tooltip con información detallada
  - ID de la plaza
  - Estado actual
  - Parking ID
  - Nivel
  - Temperatura del sensor
  - Nivel de batería
  - Última actualización

### Auto-actualización

- Refresco automático cada **5 segundos**
- Indicador de conexión (Online/Offline)
- Timestamp de última actualización
- Pausa automática cuando la pestaña no está visible

## 🧪 Testing

### Probar localmente

1. **Iniciar productor Kafka** (en VM Lubuntu):

```bash
python3 ~/smartparking/scripts/parking_producer.py
```

2. **Verificar NiFi** está procesando mensajes

3. **Verificar datos en MongoDB Atlas**:

   - Ir a Atlas UI → Browse Collections
   - Ver documentos en `smartparking.bays`

4. **Iniciar Flask** y observar cambios en tiempo real

### Probar desde dispositivo móvil

1. Conectar móvil a la misma red WiFi
2. Encontrar IP de tu PC: `ipconfig` (Windows) o `ifconfig` (Linux/Mac)
3. Acceder desde móvil: `http://TU_IP:5000`

## 📊 Monitoreo y Logs

La aplicación genera logs en `smartparking.log`:

```
2025-10-20 10:15:30 - __main__ - INFO - ✓ Conectado exitosamente a MongoDB Atlas
2025-10-20 10:15:35 - __main__ - INFO - API /api/bays: Retornadas 90 plazas
2025-10-20 10:15:40 - __main__ - INFO - API /api/stats: 45/90 ocupadas (50.0%)
```

Ver logs en tiempo real:

```bash
# Windows
type smartparking.log

# Linux/Mac
tail -f smartparking.log
```

## 🔧 Troubleshooting

### Error: "Database connection not available"

- Verificar que `.env` tiene la URI correcta
- Verificar que la contraseña no tiene caracteres especiales sin escapar
- Verificar Network Access en Atlas (IP whitelist)
- Probar conexión con `test_connection.py`

### Error: "No module named 'pymongo'"

```bash
pip install pymongo[srv] dnspython
```

### Error: "No se muestran datos"

- Verificar que NiFi está insertando datos en MongoDB Atlas
- Verificar colecciones en Atlas UI
- Revisar logs de Flask
- Abrir consola del navegador (F12) para ver errores JavaScript

### Error: "Auto-actualización no funciona"

- Verificar que no hay errores en consola del navegador
- Verificar que endpoint `/api/bays` responde correctamente
- Refrescar página (Ctrl+F5)

### La UI se ve mal en móvil

- Asegúrate de que el HTML tiene la meta tag viewport
- Limpia caché del navegador
- Prueba en modo incógnito

## 📝 Notas Importantes

- ⚠️ **Nunca** subas `.env` a Git (añádelo a `.gitignore`)
- ⚠️ La actualización cada 5 segundos puede consumir datos si usas móvil
- ⚠️ Free tier de Atlas tiene límite de 512MB de almacenamiento
- ✅ La aplicación pausa actualizaciones cuando la pestaña está oculta (ahorro de recursos)
- ✅ Compatible con Chrome, Firefox, Edge, Safari

## 📄 Licencia

Proyecto académico - Big Data Aplicado - IES Fernando Aguilar Quignon

---

**Desarrollado por**: Ángel Manuel Pereira Rodríguez
**Fecha**: Octubre 2025  
**Curso**: Big Data Aplicado - 1ª Evaluación
