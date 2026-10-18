import os
import csv
import json
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_PRINCIPAL = os.path.join(BASE, "sistema_uci")
CARPETA_JSON = os.path.join(CARPETA_PRINCIPAL, "exportaciones_json")
CARPETA_CSV = os.path.join(CARPETA_PRINCIPAL, "exportaciones_csv")
CARPETA_PACIENTES = os.path.join(BASE, "pacientes_p3")

# Carpetas y entradas del usuario

def crear_carpetas():
    # exist_ok=True: si la carpeta ya existe no pasa nada, si no, la crea
    # (también crea sistema_uci porque es la carpeta que contiene a las otras)
    for ruta in (CARPETA_JSON, CARPETA_CSV):
        os.makedirs(ruta, exist_ok=True)


def leer_entero(mensaje):
    while True:
        try:
            return int(input(mensaje))
        except ValueError:
            print("Debe ingresar un número entero.")


def listar_archivos():
    if not os.path.isdir(CARPETA_PACIENTES):
        print("No se encontró la carpeta:", CARPETA_PACIENTES)
        return
    print("\nArchivos disponibles en", CARPETA_PACIENTES)
    for nombre in sorted(os.listdir(CARPETA_PACIENTES)):
        print("  -", nombre)


def contiene_id(ruta, id_paciente):
    # Revisa que el archivo mencione al paciente (para no mezclar pacientes)
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return id_paciente in archivo.read()
    except (OSError, UnicodeDecodeError):
        return False


def pedir_ruta(mensaje, id_paciente=None):
    # Pide la ruta del archivo. Se puede escribir la ruta completa o solo
    # el nombre del archivo si está en la carpeta pacientes_p3.
    while True:
        ruta = input(mensaje).strip().strip('"')
        if ruta == "0":
            return None
        if not os.path.isfile(ruta):
            ruta = os.path.join(CARPETA_PACIENTES, ruta)
        if not os.path.isfile(ruta):
            print("No se encontró ese archivo, intente de nuevo (0 para cancelar).")
            continue
        if id_paciente is not None and not contiene_id(ruta, id_paciente):
            print("Ese archivo no corresponde al paciente", id_paciente)
            continue
        return ruta


def a_numero(texto):
    # Si el texto es un número lo devuelve como número, si no lo deja igual
    try:
        return int(texto)
    except ValueError:
        pass
    try:
        return float(texto)
    except ValueError:
        return texto

# Extracción de cada tipo de archivo

def extraer_hl7(ruta):
    # Archivo HL7 v2: cada línea es un segmento y los campos van separados por |
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            lineas = archivo.read().splitlines()
    except (OSError, UnicodeDecodeError):
        print("No se pudo leer el archivo.")
        return None

    paciente = {}
    unidad = ""
    for linea in lineas:
        campos = linea.split("|")
        if campos[0] == "PID" and len(campos) > 11:
            partes = campos[5].split("^")
            apellido = partes[0]
            nombres = " ".join(partes[1:])
            paciente["id"] = campos[3]
            paciente["nombre"] = (nombres + " " + apellido).strip().title()
            direccion = campos[11].split("^")
            paciente["direccion"] = direccion[0] + ", " + direccion[-1]
        elif campos[0] == "PV1" and len(campos) > 3:
            unidad = campos[3].replace("^", " - ")

    if "id" not in paciente:
        print("No se encontró el segmento PID, ¿es un archivo HL7?")
        return None
    paciente["ubicacion"] = unidad if unidad else "N/A"
    return paciente


def extraer_signos(ruta):
    # "{*}" sirve para ignorar el namespace del XML.
    try:
        raiz = ET.parse(ruta).getroot()
    except (ET.ParseError, OSError):
        print("No se pudo leer el XML.")
        return None

    signos = []
    for sign in raiz.findall(".//{*}sign"):
        signos.append({
            "nombre": sign.get("name"),
            "valor": a_numero(sign.get("value")),
            "unidad": sign.get("unit")
        })
    return signos


def extraer_fhir(ruta):
    # XML FHIR (DiagnosticReport): categoría, conclusión y médico
    try:
        raiz = ET.parse(ruta).getroot()
    except (ET.ParseError, OSError):
        print("No se pudo leer el XML.")
        return None

    categoria = raiz.findtext("{*}category")
    conclusion = raiz.findtext("{*}conclusion")
    medico = raiz.findtext("{*}physician")
    if categoria is None and conclusion is None and medico is None:
        print("No se encontró información de diagnóstico en el archivo.")
        return None

    return {
        "Categoria": categoria.strip() if categoria else "N/A",
        "Conclusión": conclusion.strip() if conclusion else "N/A",
        "Médico": medico.strip() if medico else "N/A"
    }


def extraer_telemetria(ruta):
    # Log de texto: fecha/hora|id_paciente|sensor|valor|estado
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            lineas = archivo.read().splitlines()
    except (OSError, UnicodeDecodeError):
        print("No se pudo leer el archivo.")
        return None

    registros = []
    for linea in lineas:
        partes = linea.strip().split("|")
        if len(partes) == 5:
            registros.append({
                "fecha_hora": partes[0],
                "id_paciente": partes[1],
                "sensor": partes[2],
                "valor": a_numero(partes[3]),
                "estado": partes[4]
            })
    return registros

# Historia clínica (diccionario general)

def leer_archivo(mensaje, extractor, id_paciente=None):
    # Repite la pregunta hasta que el archivo sirva o el usuario cancele (0)
    while True:
        ruta = pedir_ruta(mensaje, id_paciente)
        if ruta is None:
            return None
        datos = extractor(ruta)
        if datos:
            return datos
        print("No se pudo extraer información de ese archivo, revise que sea el correcto.")


def registrar_paciente(historias):
    print("\n--- Extracción de datos de un paciente ---")
    print("(escriba 0 en cualquier momento para cancelar)\n")

    hl7 = leer_archivo("Ruta del archivo HL7 (.txt): ", extraer_hl7)
    if hl7 is None:
        print("Registro cancelado.")
        return
    id_paciente = hl7["id"]
    print("Paciente encontrado:", hl7["nombre"], "-", id_paciente)

    signos = leer_archivo("Ruta del archivo de signos vitales (.xml): ",
                          extraer_signos, id_paciente)
    if signos is None:
        print("Registro cancelado.")
        return

    fhir = leer_archivo("Ruta del archivo de diagnóstico FHIR (.xml): ",
                        extraer_fhir, id_paciente)
    if fhir is None:
        print("Registro cancelado.")
        return

    telemetria = leer_archivo("Ruta del archivo de telemetría (.txt): ",
                              extraer_telemetria, id_paciente)
    if telemetria is None:
        print("Registro cancelado.")
        return

    if id_paciente in historias:
        print("El paciente ya estaba registrado, se actualizó su información.")

    historias[id_paciente] = {
        "paciente_hl7": hl7,
        "signos_vitales": signos,
        "fhir_diagnostico": fhir,
        "telemetria": telemetria
    }
    print("Historia clínica de", hl7["nombre"], "guardada correctamente.")


# Visualización

def ver_historia(historias):
    if not historias:
        print("Todavía no hay pacientes registrados.")
        return

    ids = list(historias.keys())
    print("\nPacientes registrados:")
    for i, id_paciente in enumerate(ids, start=1):
        print(f"  {i}. {id_paciente} - {historias[id_paciente]['paciente_hl7']['nombre']}")

    opcion = leer_entero("Número del paciente: ")
    if opcion < 1 or opcion > len(ids):
        print("Ese paciente no existe.")
        return

    historia = historias[ids[opcion - 1]]
    paciente = historia["paciente_hl7"]

    print("\n" + "=" * 60)
    print("HISTORIA CLÍNICA")
    print("=" * 60)
    print("Nombre:   ", paciente["nombre"])
    print("ID:       ", paciente["id"])
    print("Ubicación:", paciente["ubicacion"])
    print("Dirección:", paciente["direccion"])

    print("\nSignos vitales:")
    for s in historia["signos_vitales"]:
        print(f"  {s['nombre']}: {s['valor']} {s['unidad']}")

    diag = historia["fhir_diagnostico"]
    print("\nDiagnóstico:")
    print("  Categoría: ", diag["Categoria"])
    print("  Conclusión:", diag["Conclusión"])
    print("  Médico:    ", diag["Médico"])

    print("\nTelemetría:")
    for t in historia["telemetria"]:
        print(f"  {t['fecha_hora']} | {t['sensor']}: {t['valor']} ({t['estado']})")


def exportar_json(historias):
    if not historias:
        print("No hay pacientes para exportar.")
        return

    crear_carpetas()
    for id_paciente, historia in historias.items():
        ruta = os.path.join(CARPETA_JSON, "historia_" + id_paciente + ".json")
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(historia, archivo, indent=4, ensure_ascii=False)
        print("JSON guardado en:", ruta)


def exportar_csv(historias):
    if not historias:
        print("No hay pacientes para exportar.")
        return

    # Columnas de signos: una por cada signo distinto, con su unidad
    columnas_signos = []
    for historia in historias.values():
        for s in historia["signos_vitales"]:
            columna = f"{s['nombre']} ({s['unidad']})"
            if columna not in columnas_signos:
                columnas_signos.append(columna)

    crear_carpetas()
    ruta = os.path.join(CARPETA_CSV, "signos_vitales.csv")
    # utf-8-sig para que Excel muestre bien las tildes
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["id_paciente", "nombre"] + columnas_signos)

        for id_paciente, historia in historias.items():
            valores = {}
            for s in historia["signos_vitales"]:
                valores[f"{s['nombre']} ({s['unidad']})"] = s["valor"]

            fila = [id_paciente, historia["paciente_hl7"]["nombre"]]
            for columna in columnas_signos:
                fila.append(valores.get(columna, "N/A"))
            escritor.writerow(fila)

    print("CSV guardado en:", ruta)
