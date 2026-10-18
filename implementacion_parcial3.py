
import funciones_parcial3 as fp

# Diccionario general: llave = id del paciente, valor = su historia clínica
historias = {}


def menu():
    print("\n" + "=" * 50)
    print("   SISTEMA UCI - GESTIÓN DE INFORMACIÓN CLÍNICA")
    print("=" * 50)
    print("1. Ver archivos disponibles")
    print("2. Extraer información de un paciente")
    print("3. Ver historia clínica")
    print("4. Exportar historias a JSON")
    print("5. Exportar signos vitales a CSV")
    print("6. Salir")


def main():
    fp.crear_carpetas()

    opcion = 0
    while opcion != 6:
        menu()
        opcion = fp.leer_entero("Seleccione una opción: ")

        if opcion == 1:
            fp.listar_archivos()
        elif opcion == 2:
            fp.registrar_paciente(historias)
        elif opcion == 3:
            fp.ver_historia(historias)
        elif opcion == 4:
            fp.exportar_json(historias)
        elif opcion == 5:
            fp.exportar_csv(historias)
        elif opcion == 6:
            print("Programa finalizado.")
        else:
            print("Opción no válida.")


main()
