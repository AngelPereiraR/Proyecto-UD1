"""
SmartParking Flow - Simulador de Sensores de Aparcamiento
Genera datos simulados de sensores de parking para enviar a Kafka
"""

import json
import random
import time
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

class ParkingSensorSimulator:
    """Simula sensores de un parking inteligente de 2 plantas con 20 plazas"""
    
    def __init__(self, parking_id="PK-CADIZ-01", levels=2, bays_per_level=10):
        """
        Inicializa el simulador
        
        Args:
            parking_id: Identificador del parking
            levels: Número de plantas (niveles)
            bays_per_level: Plazas por nivel
        """
        self.parking_id = parking_id
        self.levels = levels
        self.bays_per_level = bays_per_level
        self.bays = self._initialize_bays()
        
    def _initialize_bays(self):
        """Inicializa el estado de todas las plazas"""
        bays = {}
        for level in range(1, self.levels + 1):
            for bay in range(1, self.bays_per_level + 1):
                bay_id = f"L{level}-A-{bay:03d}"
                bays[bay_id] = {
                    "bay_id": bay_id,
                    "parking_id": self.parking_id,
                    "level": f"L{level}",
                    "occupied": random.choice([True, False]),
                    "temperature_c": round(random.uniform(18.0, 28.0), 1),
                    "battery_pct": random.randint(60, 100)
                }
        return bays
    
    def generate_event(self, bay_id):
        """
        Genera un evento de sensor para una plaza específica
        
        Args:
            bay_id: Identificador de la plaza
            
        Returns:
            dict: Documento JSON del evento
        """
        bay = self.bays[bay_id]
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Simular cambio de temperatura y batería
        bay["temperature_c"] = round(bay["temperature_c"] + random.uniform(-0.5, 0.5), 1)
        bay["temperature_c"] = max(15.0, min(35.0, bay["temperature_c"]))
        
        # La batería disminuye lentamente
        if random.random() < 0.1:  # 10% de probabilidad de decrementar
            bay["battery_pct"] = max(20, bay["battery_pct"] - 1)
        
        event = {
            "bay_id": bay["bay_id"],
            "parking_id": bay["parking_id"],
            "level": bay["level"],
            "occupied": bay["occupied"],
            "last_event_ts": now,
            "metrics": {
                "temperature_c": bay["temperature_c"],
                "battery_pct": bay["battery_pct"]
            },
            "updated_at": now
        }
        
        return event
    
    def simulate_vehicle_movement(self):
        """Simula la entrada o salida de un vehículo cambiando el estado de una plaza"""
        bay_id = random.choice(list(self.bays.keys()))
        self.bays[bay_id]["occupied"] = not self.bays[bay_id]["occupied"]
        return bay_id
    
    def get_parking_status(self):
        """Retorna estadísticas del parking"""
        total = len(self.bays)
        occupied = sum(1 for bay in self.bays.values() if bay["occupied"])
        free = total - occupied
        
        return {
            "total_bays": total,
            "occupied": occupied,
            "free": free,
            "occupancy_rate": round((occupied / total) * 100, 1)
        }


class KafkaPublisher:
    """Publica eventos de sensores a Kafka"""
    
    def __init__(self, bootstrap_servers='localhost:9092', topic='parking-events'):
        """
        Inicializa el productor de Kafka
        
        Args:
            bootstrap_servers: Servidor(es) de Kafka
            topic: Tópico donde publicar los eventos
        """
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
        
    def publish_event(self, event):
        """
        Publica un evento en Kafka
        
        Args:
            event: Diccionario con los datos del evento
        """
        try:
            future = self.producer.send(self.topic, value=event)
            record_metadata = future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"Error al enviar mensaje a Kafka: {e}")
            return False
    
    def close(self):
        """Cierra la conexión con Kafka"""
        self.producer.flush()
        self.producer.close()


def run_simulation(kafka_servers='localhost:9092', 
                   topic='parking-events',
                   interval=3,
                   event_probability=0.3):
    """
    Ejecuta la simulación del parking
    
    Args:
        kafka_servers: Servidor(es) de Kafka
        topic: Tópico de Kafka
        interval: Segundos entre actualizaciones
        event_probability: Probabilidad de que ocurra un cambio de estado
    """
    print("=" * 60)
    print("SmartParking Flow - Simulador de Sensores")
    print("=" * 60)
    print(f"Kafka Servers: {kafka_servers}")
    print(f"Topic: {topic}")
    print(f"Intervalo: {interval} segundos")
    print("=" * 60)
    
    # Inicializar simulador y publisher
    simulator = ParkingSensorSimulator()
    publisher = KafkaPublisher(bootstrap_servers=kafka_servers, topic=topic)
    
    print("\nEstado inicial del parking:")
    status = simulator.get_parking_status()
    print(f"  Total plazas: {status['total_bays']}")
    print(f"  Ocupadas: {status['occupied']}")
    print(f"  Libres: {status['free']}")
    print(f"  Tasa ocupación: {status['occupancy_rate']}%")
    print("\n" + "=" * 60)
    print("Iniciando simulación... (Ctrl+C para detener)")
    print("=" * 60 + "\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            
            # Decidir si hay movimiento de vehículos
            if random.random() < event_probability:
                bay_id = simulator.simulate_vehicle_movement()
                event = simulator.generate_event(bay_id)
                
                # Publicar en Kafka
                if publisher.publish_event(event):
                    action = "ENTRADA" if event["occupied"] else "SALIDA"
                    print(f"[{iteration:04d}] {action} en {bay_id} "
                          f"(Temp: {event['metrics']['temperature_c']}°C, "
                          f"Batería: {event['metrics']['battery_pct']}%)")
                else:
                    print(f"[{iteration:04d}] ERROR al publicar evento para {bay_id}")
            
            # Cada 10 iteraciones, mostrar estadísticas
            if iteration % 10 == 0:
                status = simulator.get_parking_status()
                print(f"\n--- Estado del parking (iteración {iteration}) ---")
                print(f"Ocupadas: {status['occupied']}/{status['total_bays']} "
                      f"({status['occupancy_rate']}%)")
                print("-" * 50 + "\n")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Simulación detenida por el usuario")
        print("=" * 60)
    finally:
        publisher.close()
        print("\nEstadísticas finales:")
        status = simulator.get_parking_status()
        print(f"  Ocupadas: {status['occupied']}/{status['total_bays']}")
        print(f"  Libres: {status['free']}")
        print(f"  Tasa ocupación: {status['occupancy_rate']}%")


if __name__ == "__main__":
    import argparse
    
    # Parser de argumentos para configuración flexible
    parser = argparse.ArgumentParser(description='Simulador de Sensores de Parking')
    parser.add_argument('--kafka-server', 
                       default='localhost:9092',
                       help='Dirección del servidor Kafka (ej: 192.168.1.100:9092)')
    parser.add_argument('--topic', 
                       default='parking-events',
                       help='Nombre del tópico de Kafka')
    parser.add_argument('--interval', 
                       type=int, 
                       default=3,
                       help='Segundos entre eventos')
    parser.add_argument('--probability', 
                       type=float, 
                       default=0.3,
                       help='Probabilidad de cambio de estado (0.0-1.0)')
    
    args = parser.parse_args()
    
    run_simulation(
        kafka_servers=args.kafka_server,
        topic=args.topic,
        interval=args.interval,
        event_probability=args.probability
    )