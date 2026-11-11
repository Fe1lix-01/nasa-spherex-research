#Esta es importante ya que aqui podremos obtener las imaganes para la linea temporal que se mostrara
#Falta que el script pueda analizar diferentes csv que generen las cordenadas
import csv
from pathlib import Path

ruta = Path(
    "labs/science/outputs/practica07_barnard/"
    "barnard_observaciones_D2.csv"
)

with ruta.open(encoding="utf-8", newline="") as file:
    observaciones = list(csv.DictReader(file))

print("Total:", len(observaciones))

# Primera y última observación
primera = observaciones[0]
ultima = observaciones[-1]

print("Primera:", primera["date_utc"])
print("Última:", ultima["date_utc"])

# Calcular la separación temporal en días
mjd_inicial = float(primera["mjd"])
mjd_final = float(ultima["mjd"])

diferencia = mjd_final - mjd_inicial

print(f"Separación: {diferencia:.2f} días")

# Contar los registros de cada release
qr2 = [r for r in observaciones if r["release"] == "spherex_qr2"]
qr3 = [r for r in observaciones if r["release"] == "spherex_qr3"]

print("QR2:", len(qr2))
print("QR3:", len(qr3))
