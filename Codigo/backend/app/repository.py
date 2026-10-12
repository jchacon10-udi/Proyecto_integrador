"""Repositorio de fixtures ficticios: volátil y aislado por aplicación.

No simula transacciones Oracle. El bloqueo protege cada operación atómica demo
en un proceso; no ofrece persistencia ni concurrencia entre múltiples procesos.
"""
from datetime import date
from threading import RLock
from .domain import Jornada, Gasto

class MemoryRepository:
    def __init__(self):
        self.lock = RLock()
        self.gastos: dict[int, Gasto] = {}
        self.jornadas: dict[int, Jornada] = {}
        self.closed_homes: set[int] = set()
        self.audit: list[dict] = []
        self.next_id = 1
        self.unidades = {1:"Centímetros cúbicos",2:"Litro",3:"Gramos",4:"Onzas",5:"Libra",6:"Kilo",7:"Arroba",8:"Otra"}
        self.formas = {1:"Compra",2:"Pago por trabajo",3:"Regalo o donación",4:"Trueque",5:"Producción propia",6:"Negocio del hogar",7:"Otra"}
        # Subconjunto de catálogos para esta demo; no se inventa una carga real.
        self.lugares = {1:"Supermercado",6:"Tienda de barrio",10:"Plaza de mercado"}
        self.frecuencias = {2:"Diario",3:"Semanal",4:"Quincenal",5:"Mensual",9:"Esporádica"}
        for day in range(1,15):
            self.add_jornada(Jornada(day,1,day,date(2026,9,day),date(2026,9,1)))
        self.add_jornada(Jornada(26,2,6,date(2026,9,6),date(2026,9,1)))

    def add_jornada(self, jornada: Jornada):
        with self.lock:
            if jornada.id in self.jornadas or any(j.hogar_id==jornada.hogar_id and j.dia==jornada.dia for j in self.jornadas.values()):
                raise ValueError("Jornada duplicada por hogar/día")
            self.jornadas[jornada.id] = jornada
