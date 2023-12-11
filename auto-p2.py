# Andres Herencia Lopez-Menchero
# Patricia Fernandez Sastre
# Fernando Herrera Pozo

#########################################################
################# PRÁCTICA CREATIVA 1 ###################
#########################################################

# Importamos los modulos necesarios

import sys
import os
from subprocess import call
from lxml import etree
import json

orden = ["prepare", "launch", "stop", "release", "restart", "watch", "help"]

def ejecucion():

    if (len(sys.argv) < 2 or sys.argv[1] not in orden):
        raise Exception("Por favor, selecciona una orden a ejecutar entre las disponibles: prepare, launch, stop, release. Para saber lo que hace cada una, escriba 'python3 auto-p2.py help")   
    
    orden_exe = funcion_exe[sys.argv[1]]

    if (len(sys.argv) == 3): 
    # para aquellas órdenes que requieran de un parámetro
        orden_exe(sys.argv[2])
    elif (len(sys.argv) == 4): 
    # para restart
        orden_exe(sys.argv[2], sys.argv[3])
    else:
        orden_exe() #para aquellas órdenes que no requieran de un parámetro

#####################################################################
# > help: ofrece documentación e información sobre lo que hace cada
# orden. Dice también los valores por defecto que obtiene cada 
# parámetro de una función.
#####################################################################

def help():
    help = """Las ordenes que puede ejcutar esta script son:

    > prepare [num_serv]: crea los ficheros .qcow2 en diferencias y los de especificación en XML de cada MV, 
      así como los bridges virtuales que soportan las LAN del escenario.
        [num_serv]: número de servidores que queremos arrancar. Soporta entre 1 y 5. El valor por defecto es 3.

    > launch [type]: arranca las MMVV y muestra su consola.
	[type]: máquina virtual a arrancar. Arranca todas por defecto.

    > stop [type]: para las máquinas virtuales. NO las libera.
	[type]: máquina virtual a arrancar. Arranca todas por defecto

    > release: libera (limpia) el escenario, borrando todos los ficheros creados.

    > restart [num_serv] [type_all]: reinicia el escenario. A la hora de 
    arrancar, se puede elegir cuantos servidores queremos que estén activos y 
    cuales máquinas lanzar.
           [num_serv]: número de servidores que queremos arrancar. Soporta entre 1 y 5. El valor por defecto es 3.
           [type]: máquina virtual a arrancar. Arranca todas por defecto.

    > watch: presenta el estado de todas las máquinas virtuales del escenario.

    """
    print(help)

####################################################################
# > prepare [num_serv]: crea los ficheros .qcow2 en diferencias y
# los de especificación en XML de cada MV, así como los bridges 
# virtuales que soportan las LAN del escenario.
#       [num_serv]: número de servidores que queremos arrancar. 
#       Soporta entre 1 y 5. El valor por defecto es 3.
####################################################################

def prepare(num_serv = 3):

    # Comprobación inicial de que el directorio tiene los ficheros correctos. 
    # En teoría partimos de un directorio que contiene la plantilla XML y la imagen qcow2 necesarias

    if not os.path.isfile("cdps-vm-base-pc1.qcow2"):
        call(["cp", "/lab/cdps/pc1/cdps-vm-base-pc1.qcow2", "cdps-vm-base-pc1.qcow2"])

    if not os.path.isfile("plantilla-vm-pc1.xml"):
        call(["cp", "/lab/cdps/pc1/plantilla-vm-pc1.xml", "plantilla-vm-pc1.xml"])

    if os.path.isfile("auto-p2.json"):
        raise Exception("El escenario ya ha sido preparado, si desea rearrancarlo, use el comando 'restart' [num_serv] [type]")

    num_serv = int(num_serv)

    #### Antes de nada, guardamos en un json el número de servidores que hemos preparado, que usaremos para otras órdenes
    configuration = {"num_serv": num_serv}
    if ((num_serv < 1) or (num_serv > 5)):
        raise Exception("Por favor, asigna un número de servidores válido: 1, 2, 3, 4 ó 5. Por defecto, se tomarán 3 servidores.")

    with open("auto-p2.json", "w") as f:
        json.dump(configuration, f, indent = 4)

    #### Para las máquinas virtuales s1, s2 ...
    for i in range(1, num_serv+1):
        s = "s{}".format(i)

        call(["qemu-img", "create", "-f", "qcow2", "-b", "cdps-vm-base-pc1.qcow2", "{}.qcow2".format(s)])
        call(["cp", "plantilla-vm-pc1.xml", "{}.xml".format(s)])

        # Ahora debemos de llamar para cada caso a una función auxiliar que permita modificar el xml con los valores correctos
        # Cada una de las MMVVs se conecta a LAN2. También la definimos con virsh.
        mod_xml(s,"LAN2")
        call(["sudo", "virsh", "define", "{}.xml".format(s)])
        create_vm_lb_c1(s)

    #### Configuración, creación y definición de lb

    call(["qemu-img", "create", "-f", "qcow2", "-b", "cdps-vm-base-pc1.qcow2", "lb.qcow2"])
    call(["cp", "plantilla-vm-pc1.xml", "lb.xml"])
    # Creamos otra función auxiliar porque necesitamos dos interfaces y no una
    mod_xml_lb()
    call(["sudo", "virsh", "define", "lb.xml"])
    create_vm_lb_c1("lb")

    #### Configuración, creación y definición de c1

    call(["qemu-img", "create", "-f", "qcow2", "-b", "cdps-vm-base-pc1.qcow2", "c1.qcow2"])
    call(["cp", "plantilla-vm-pc1.xml", "c1.xml"])
    mod_xml("c1","LAN1") 
    call(["sudo", "virsh", "define", "c1.xml"])
    create_vm_lb_c1("c1")

    if (os.path.isfile("s1.qcow2") and os.path.isfile("lb.qcow2") and os.path.isfile("c1.qcow2")):
        print("Archivos qcow2 creados correctamente")
    else:
        raise Exception("Ha habido un error en la creación de los ficheros qcow2")

    if (os.path.isfile("s1.xml") and os.path.isfile("lb.xml") and os.path.isfile("c1.xml")):
        print("Archivos xml creados correctamente")
    else:
        raise Exception("Ha habido un error en la creación de los ficheros xml")

    #### Ahora debemos de crear los bridges y habilitar las LAN

    call(["sudo","brctl","addbr","LAN1"])
    call(["sudo","brctl","addbr","LAN2"])
    call(["sudo","ifconfig","LAN1","up"])
    call(["sudo","ifconfig","LAN2","up"])

    #### Arrancamos el gestor de máquinas virtuales. NO las máquinas, que se hará en launch
    
    call(["HOME=/mnt/tmp", "sudo", "virt-manager"], shell=True)
    
    #### Configuración de red SOLO del HOST 

    call(["sudo","ifconfig","LAN1","10.10.1.3/24"])      
    call(["sudo","ip","route","add","10.10.0.0/16","via","10.10.1.1"]) 

    # Configuración de HAProxy

    HAProxy(num_serv)

###########################################################################
# > launch [type]: arranca las MMVV y muestra su consola.
#          [type]: máquina virtual a arrancar. Arranca todas por defecto.
###########################################################################

def launch(type = "all"):
    if os.path.isfile("auto-p2.json"):
        with open("auto-p2.json", 'r') as f:
            lines = f.read()
            jsonDecoded = json.loads(lines)
    else: 
        raise Exception("Las máquinas no han sido creadas o no existe el fichero json de configuración. Usa el comando 'prepare' para crearlas.")
    num_serv = jsonDecoded["num_serv"]

    # Arrancamos todas por defecto
    
    if (type == "all"):
        call(["sudo", "virsh", "start", "lb"])
        os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'lb' -e 'sudo virsh console lb' &")
        print("máquina 'lb' arrancada correctamente")
        call(["sudo", "virsh", "start", "c1"])
        os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'c1' -e 'sudo virsh console c1' &")
        print("máquina 'c1' arrancada correctamente")
        for i in range(1, num_serv + 1):
            name = "s{}".format(i)
            call(["sudo", "virsh", "start", "{}".format(name)])
            os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title '{}' -e 'sudo virsh console {}' &".format(name,name))
            print("máquinas 's' arrancadas correctamente")
    else:
    # Arrancamos de manera individual, si se especifica por parámetro
        call(["sudo", "virsh", "start", "{}".format(type)])
        os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title '{}' -e 'sudo virsh console {}' &".format(type, type))
        print("La máquina ha sido arrancada")

######################################################################
# > stop [type]: para las máquinas virtuales. NO las libera.
#        [type]: máquina virtual a arrancar. Arranca todas por defecto
######################################################################

def stop(type = "all"):
    if os.path.isfile("auto-p2.json"):
        with open("auto-p2.json", 'r') as f:
            lines = f.read()
            jsonDecoded = json.loads(lines)
    else: 
        raise Exception("Las máquinas no han sido creadas o no existe el fichero json de configuración. Usa el comando 'prepare' para crearlas.")
    num_serv = jsonDecoded["num_serv"]

    # Paramos todas por defecto

    if (type == "all"):
        call(["sudo", "virsh", "shutdown", "lb"])
        call(["sudo", "virsh", "shutdown", "c1"])
        for i in range(1, num_serv + 1):
            name = "s{}".format(i)
            call(["sudo", "virsh", "shutdown", "{}".format(name)])
    else:
    # Paramos de manera individual, si se especifica por parámetro
        call(["sudo", "virsh", "shutdown", "{}".format(type)])

###################################################################
#  > release: libera (limpia) el escenario, borrando todos los 
#  ficheros creados.
###################################################################

def release():
    if os.path.isfile("auto-p2.json"):
    	with open("auto-p2.json", 'r') as f:
            lines = f.read()
            jsonDecoded = json.loads(lines)
    else:
        raise Exception("Ha habido un error en la creacion del json o el json de configuración no ha sido creado. Vuelva a ejecutar 'release' o ejecuta la función 'getjson' para crearlo de cero")
    num_serv = jsonDecoded["num_serv"]

    # Destruir, quitar la definición de los servidores s1, s2 ... y borrar archivos

    for i in range(1,num_serv+1):
        call(["sudo","virsh","destroy","s{}".format(i)])
        call(["sudo","virsh","undefine","s{}".format(i)])
        call("rm -rf s{}*".format(i),shell=True) 
        # ponemos asterisco para borrar tanto la extensión qcow2 como la extensión xml
    
    # Destruir, quitar la definición de lb y c1 y borrar archivos
        
    call(["sudo","virsh","destroy","lb"])
    call(["sudo","virsh","undefine","lb"])
    call("rm -rf lb*",shell=True)

    call(["sudo","virsh","destroy","c1"])
    call(["sudo","virsh","undefine","c1"])
    call("rm -rf c1*",shell=True)

    # Borramos el resto de archivos

    call("rm -rf interfaces", shell=True)
    call("rm -r auto-p2.json",shell=True)
    call("rm -r hostname",shell=True)
    call("rm -r haproxy.cfg", shell=True)

    # Dropeamos también la configuración de LAN1 y LAN2

    call(["sudo","ifconfig","LAN1","down"])
    call(["sudo","brctl","delbr","LAN1"])
    call(["sudo","ifconfig","LAN2","down"])
    call(["sudo","brctl","delbr","LAN2"]) 

#########################################################################
# > watch: presenta el estado de todas las máquinas virtuales del 
# escenario.
#########################################################################

def watch(): 
    os.system("xterm -title monitor -e watch sudo virsh list --all &")
    raise Exception("Monitor creado correctamente")

##########################################################################
# > restart [num_serv] [type_all]: reinicia el escenario. A la hora de 
# arrancar, se puede elegir cuantos servidores queremos que estén activos y 
# cuales máquinas lanzar.
#           [num_serv]: número de servidores que queremos arrancar. 
# Soporta entre 1 y 5. El valor por defecto es 3.
#           [type]: máquina virtual a arrancar. Arranca todas por defecto
##########################################################################

def restart(num_serv = 3, type = "all"):
    if not os.path.isfile("auto-p2.json"):
        raise Exception("El escenario aún no ha sido arrancado.")
    n = num_serv
    t = type
    stop()
    release()
    prepare(n)
    launch(t)  

#### FUNCIONES AUXILIARES ####   

def mod_xml(name, lan):
    ruta_abs = str(os.getcwd())

    # Obtener el arbol XML y su raíz.

    tree = etree.parse("{}.xml".format(name))
    root = tree.getroot()

    # Definir la ruta y el nombre del fichero qcow2

    dominio = root.find("name")
    dominio.text = "{}".format(name)

    sourcefile = root.find("./devices/disk/source")
    sourcefile.set("file", '{}/{}.qcow2'.format(ruta_abs,name))

    # definir las interfaces a los que está conectado (LAN1 o LAN2)

    bridge = root.find("./devices/interface/source")
    bridge.set("bridge", lan)

    # Escribimos cada uno de los resultados

    with open("{}.xml".format(name),"w") as f:
        f.write(etree.tounicode(tree, pretty_print=True))

def mod_xml_lb():
    ruta_abs = str(os.getcwd())
    
    tree = etree.parse("lb.xml")  
    root = tree.getroot()
      
    domname = root.find("name")
    domname.text = "lb"

    sourcefile = root.find("./devices/disk/source")
    sourcefile.set("file", '{}/lb.qcow2'.format(ruta_abs))
      
    bridge = root.find("./devices/interface/source")
    bridge.set("bridge", "LAN2")

    dv = root.find("./devices")

    inf = etree.Element("interface")
    inf.set("type",'bridge')
    dv.insert(2, inf)
        
    sc = etree.Element("source")
    sc.set("bridge",'LAN1')
    inf.insert(1, sc)
      
    md = etree.Element("model")
    md.set("type",'virtio')
    inf.insert(1, md) 

    with open("lb.xml","w") as f:
        f.write(etree.tounicode(tree,pretty_print=True))

def create_vm_lb_c1(type):

    #### Configurar las interfaces de red
    # para lb 

    if type == "lb":
        s = """auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 10.10.1.1
    netmask 255.255.255.0
        
auto eth1
iface eth1 inet static
    address 10.10.2.1
    netmask 255.255.255.0
"""
        modfw = "s/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/"
        os.system("sudo virt-edit -a lb.qcow2 /etc/sysctl.conf -e \'{}\'".format(modfw))

    # para c1

    if type == "c1":
        s =  """auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 10.10.1.2
    netmask 255.255.255.0
    gateway 10.10.1.1
"""
    # Para los si; i = 1, 2, 3 ...

    if type[0] == "s":
        s_address = "10.10.2.1{}".format(type[1])
        s = """auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address {}
    netmask 255.255.255.0
    gateway 10.10.2.1
""".format(s_address)

    # escribimos el contenido en el fichero correspondiente y copiamos los cambios en /etc/network/interfaces

    with open("interfaces","w") as f:
        f.write(s)

    call(["sudo","virt-copy-in","-a","{}.qcow2".format(type),"interfaces","/etc/network"])

    #### Configuramos el hostname y lo copiamos a la ruta correspondiente

    with open("hostname","w") as f:
        f.write("\n{}\n".format(type))
        call(["sudo","virt-copy-in","-a","{}.qcow2".format(type),"hostname","/etc"])


def HAProxy(num_serv):

    call(["sudo", "virt-copy-out", "-a", "lb.qcow2", "/etc/haproxy/haproxy.cfg", "."])
    call(["cp", "haproxy.cfg", "haproxy.cfg2"])

    aux = """frontend lb
bind *:80
mode http
default_backend webservers
backend webservers
mode http
balance roundrobin"""

    with open("haproxy.cfg2", "a") as f:
        f.write(aux)
        for i in range(1,num_serv + 1):
            f.write("server s{} 10.10.2.1{}:80 check".format(i,i))

    call(["mv", "-f", "haproxy.cfg2", "haproxy.cfg"])
    call(["sudo","virt-copy-in","-a","lb.qcow2","haproxy.cfg","/etc/haproxy"])

    print("HAProxy configurado correctamente")

#### EJECUCIÓN ####

# Función a ejecutar

funcion_exe = {orden[0]:prepare, orden[1]:launch, orden[2]:stop, orden[3]:release, orden[4]:restart, orden[5]:watch, orden[6]:help}

ejecucion()

########################## PARTES OPCIONALES REALIZADAS ###############################
#
# Funcionalidad para parar y/o arrancar MVs individualmente
#
# La monitorización del escenario mediante, por ejemplo, una orden adicional
# (monitor) que presente el estado de todas las máquinas virtuales del escenario. Esta
# orden se puede ejecutar con el comando watch para monitorizar periódicamente el
# escenario.
#
# Nueva orden restart, con la que poder reiniciar el escenario entero.
#
# Configuración del balanceador de tráfico HAproxy, de manera que cuando se arranque la
# MV esté disponible automáticamente el servicio de balanceo de tráfico entre servidores
# web.
#
# Tratamiento de errores
#
#######################################################################################
