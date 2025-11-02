"""
SmartParking Flask Application
Visualización en tiempo real del estado del parking inteligente
Conecta a MongoDB Atlas para obtener datos actualizados
"""

from flask import Flask, render_template, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smartparking.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Crear aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Configuración de MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB', 'smartparking')

# Conectar a MongoDB Atlas
db = None
try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    # Verificar conexión
    client.admin.command('ping')
    db = client[MONGO_DB]
    logger.info(f"V Conectado exitosamente a MongoDB Atlas - Base de datos: {MONGO_DB}")
except ConnectionFailure as e:
    logger.error(f"X Error de conexión a MongoDB Atlas: {e}")
    db = None
except Exception as e:
    logger.error(f"X Error inesperado conectando a MongoDB: {e}")
    db = None


# ==================== RUTAS DE LA APLICACIÓN ====================

@app.route('/')
def index():
    """
    Página principal - Mapa visual del parking
    """
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    """
    Endpoint de health check para verificar estado del servicio
    
    Returns:
        JSON con estado del servicio y conexión a BD
    """
    if db is None:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "timestamp": datetime.now().isoformat()
        }), 503
    
    try:
        db.command('ping')
        total_bays = db.bays.count_documents({})
        total_events = db.events.count_documents({})
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "total_bays": total_bays,
            "total_events": total_events,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503


@app.route('/api/bays')
def get_bays():
    """
    Obtener todas las plazas del parking
    
    Returns:
        JSON con array de plazas ordenadas por bay_id
    """
    if db is None:
        logger.error("Base de datos no disponible")
        return jsonify({"error": "Database connection not available"}), 503
    
    try:
        # Query optimizada con proyección
        bays = list(db.bays.find(
            {},
            {
                '_id': 0,
                'bay_id': 1,
                'parking_id': 1,
                'level': 1,
                'occupied': 1,
                'last_event_ts': 1,
                'metrics': 1,
                'updated_at': 1
            }
        ).sort('bay_id', 1))
        
        logger.info(f"API /api/bays: Retornadas {len(bays)} plazas")
        
        return jsonify({
            "success": True,
            "count": len(bays),
            "data": bays,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error en /api/bays: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """
    Obtener estadísticas generales del parking
    
    Returns:
        JSON con total, ocupadas, libres, porcentaje y estadísticas por nivel
    """
    if db is None:
        logger.error("Base de datos no disponible")
        return jsonify({"error": "Database connection not available"}), 503
    
    try:
        # Estadísticas generales
        total = db.bays.count_documents({})
        occupied = db.bays.count_documents({"occupied": True})
        free = total - occupied
        occupancy_rate = round((occupied / total * 100), 2) if total > 0 else 0
        
        # Estadísticas por nivel usando agregación
        pipeline = [
            {
                "$group": {
                    "_id": "$level",
                    "total": {"$sum": 1},
                    "occupied": {
                        "$sum": {"$cond": ["$occupied", 1, 0]}
                    },
                    "free": {
                        "$sum": {"$cond": ["$occupied", 0, 1]}
                    },
                    "avg_temperature": {"$avg": "$metrics.temperature_c"},
                    "avg_battery": {"$avg": "$metrics.battery_pct"},
                    "low_battery_count": {
                        "$sum": {
                            "$cond": [
                                {"$lt": ["$metrics.battery_pct", 20]},
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        by_level = list(db.bays.aggregate(pipeline))
        
        # Formatear resultados por nivel
        levels_stats = []
        for level in by_level:
            levels_stats.append({
                "level": level["_id"],
                "total": level["total"],
                "occupied": level["occupied"],
                "free": level["free"],
                "occupancy_rate": round((level["occupied"] / level["total"] * 100), 2) if level["total"] > 0 else 0,
                "avg_temperature": round(level["avg_temperature"], 1) if level["avg_temperature"] else None,
                "avg_battery": round(level["avg_battery"], 1) if level["avg_battery"] else None,
                "low_battery_sensors": level["low_battery_count"]
            })
        
        stats = {
            "success": True,
            "total": total,
            "occupied": occupied,
            "free": free,
            "occupancy_rate": occupancy_rate,
            "levels": levels_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"API /api/stats: {occupied}/{total} ocupadas ({occupancy_rate}%)")
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error en /api/stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/bays/level/<level>')
def get_bays_by_level(level):
    """
    Obtener plazas de un nivel específico
    
    Args:
        level (str): Nivel del parking (L1, L2, L3, etc.)
    
    Returns:
        JSON con array de plazas del nivel solicitado
    """
    if db is None:
        return jsonify({"error": "Database connection not available"}), 503
    
    try:
        level_upper = level.upper()
        
        bays = list(db.bays.find(
            {"level": level_upper},
            {'_id': 0}
        ).sort('bay_id', 1))
        
        if not bays:
            logger.warning(f"No se encontraron plazas para nivel {level_upper}")
            return jsonify({
                "success": True,
                "level": level_upper,
                "count": 0,
                "data": [],
                "message": f"No hay plazas en el nivel {level_upper}"
            }), 200
        
        logger.info(f"API /api/bays/level/{level_upper}: {len(bays)} plazas")
        
        return jsonify({
            "success": True,
            "level": level_upper,
            "count": len(bays),
            "data": bays
        }), 200
        
    except Exception as e:
        logger.error(f"Error en /api/bays/level/{level}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/maintenance/low-battery')
def get_low_battery_bays():
    """
    Obtener plazas con batería baja que requieren mantenimiento
    
    Returns:
        JSON con plazas que tienen batería < 20%
    """
    if db is None:
        return jsonify({"error": "Database connection not available"}), 503
    
    try:
        low_battery_threshold = 20
        
        low_battery_bays = list(db.bays.find(
            {"metrics.battery_pct": {"$lt": low_battery_threshold}},
            {'_id': 0}
        ).sort('metrics.battery_pct', 1))
        
        # Clasificar por prioridad
        urgent = [b for b in low_battery_bays if b['metrics']['battery_pct'] < 10]
        high = [b for b in low_battery_bays if 10 <= b['metrics']['battery_pct'] < 20]
        
        logger.warning(f"Mantenimiento: {len(low_battery_bays)} sensores con batería baja")
        
        return jsonify({
            "success": True,
            "total_count": len(low_battery_bays),
            "urgent_count": len(urgent),
            "high_priority_count": len(high),
            "urgent": urgent,
            "high_priority": high,
            "threshold": low_battery_threshold
        }), 200
        
    except Exception as e:
        logger.error(f"Error en /api/maintenance/low-battery: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== MANEJADORES DE ERRORES ====================

@app.errorhandler(404)
def not_found(error):
    """Manejador para errores 404"""
    return jsonify({
        "success": False,
        "error": "Endpoint no encontrado",
        "code": 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Manejador para errores 500"""
    logger.error(f"Error interno del servidor: {error}")
    return jsonify({
        "success": False,
        "error": "Error interno del servidor",
        "code": 500
    }), 500


@app.errorhandler(503)
def service_unavailable(error):
    """Manejador para errores 503"""
    return jsonify({
        "success": False,
        "error": "Servicio no disponible",
        "code": 503
    }), 503


# ==================== PUNTO DE ENTRADA ====================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Iniciando SmartParking Flask Application")
    logger.info("=" * 60)
    logger.info(f"Base de datos: {MONGO_DB}")
    logger.info(f"Servidor: http://localhost:5000")
    logger.info("=" * 60)
    
    # Ejecutar aplicación
    app.run(
        host='localhost',
        port=5000,
        debug=True
    )