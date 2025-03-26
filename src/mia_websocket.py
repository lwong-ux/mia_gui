import asyncio
import websockets
import threading
import json
import time

# URL del servidor Rails SysQB en la Mac / ruta del WebSocket (Action Cable) declarada en config/environments/development.rb
URL = "ws://192.168.1.129:3000/cable" 

class WebSocketCliente:
    def __init__(self, gui, contador):
        self.url = URL
        self.gui = gui
        self.contador = contador
        self.ws = None
        self.is_running = False
    

    def connect(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self._run_forever, daemon=True).start()

    def _run_forever(self):
        asyncio.run(self._ciclo_infinito())

    async def _ciclo_infinito(self):
        async with websockets.connect(self.url, ping_interval=20, ping_timeout=10) as websocket:
            
            # Mensaje para suscribirse al canal "DeviceChannel"
            mensaje_suscribir = {
                "command": "subscribe",
                "identifier": json.dumps({"channel": "DeviceChannel"})
            }
            await websocket.send(json.dumps(mensaje_suscribir))
            print("✅ Conectado al WebSocket de Rails desde la Raspberry Pi")
            self.gui.despliega_mensaje_tx("Conectado al WebSocket de Rails desde la Raspberry Pi.\n")
            
            while self.is_running:
                try:
                    respuesta_servidor = await websocket.recv()
                    data = json.loads(respuesta_servidor)
                    print("🔄 Respuesta del servidor:", data)
                    
                    # Si el mensaje es un "ping", simplemente se ignora para mantener la conexión
                    if data.get("type") == "ping":
                        print("📡 Keep-Alive recibido del servidor")
                        self.gui.despliega_mensaje_rx("Keep-Alive recibido del servidor")
                        continue
                        
                    if 'message' in data:
                        self.gui.despliega_mensaje_rx(f"{data['message']}")

                    ok = self.contador.lee_ok()
                    ng = self.contador.lee_ng()
                    mesa = self.gui.lee_mesa()
                    
                    # Envía datos periódicamente al canal "DeviceChannel" de Rails
                    data = {
                        "command": "message",
                        "identifier": json.dumps({"channel": "DeviceChannel"}),
                        "data": json.dumps({"mesa": mesa, "piezas_ok": ok, "piezas_ng": ng})
                    }
                    await websocket.send(json.dumps(data))
                    print("📡 Enviado:", data)
                    self.gui.despliega_mensaje_tx(f"{data['data']}")

                    await asyncio.sleep(1)  # Enviar datos cada 1 segundo

                except websockets.exceptions.ConnectionClosed:
                    print("❌ Conexión WebSocket cerrada. Reintentando en 5 segundos...")
                    await asyncio.sleep(5)
                    return await self.connect()  # Reintenta conexión
            
    def _send_subscription_message(self):
        subscription_message = {
            "command": "subscribe",
            "identifier": json.dumps({"channel": "DeviceChannel"})
        }
        self.ws.send(json.dumps(subscription_message))

    def _send_periodic_data(self):
        self.ok += 1
        self.ng = self.ok // 9
        data = {
            "command": "message",
            "identifier": json.dumps({"channel": "DeviceChannel"}),
            "data": json.dumps({"mesa": 3, "piezas_ok": self.ok, "piezas_ng": self.ng})
        }
        self.ws.send(json.dumps(data))

    def disconnect(self):
        self.is_running = False

    def on_message(self, ws, message):
        print(f"Message received: {message}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")

    def send_message(self, message):
        if self.is_running and self.ws:
            self.ws.send(message)