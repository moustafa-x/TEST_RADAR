# Python + Arduino-based Radar Plotter
#
# ** Fonctionne avec n'importe quel moteur produisant une rotation angulaire
# ** et avec n'importe quel capteur de distance (HC-SR04, VL53L0x, LIDAR)
#
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import serial, sys, glob
import serial.tools.list_ports as COMs

############################################
# Recherche des ports Arduino, sélection d'un port, puis démarrage de la communication
############################################
matplotlib.use('TkAgg')

def port_search():
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):  # Linux
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('cygwin'):  
        ports = ['COM{0:1.0f}'.format(ii) for ii in range(1, 256)]
    elif sys.platform.startswith('darwin'):  # MAC
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Machine Not pyserial Compatible')

    arduinos = []
    for port in ports:  # boucle pour déterminer si le port est accessible
        if len(port.split('Bluetooth')) > 1:
            continue
        try:
            ser = serial.Serial(port)
            ser.close()
            arduinos.append(port)  # si nous pouvons l'ouvrir, considérons-le comme un Arduino
        except (OSError, serial.SerialException):
            pass
    return arduinos

arduino_ports = port_search()
ser = serial.Serial(arduino_ports[0], baudrate=115200)  # correspondance du débit avec l'Arduino
ser.flush()  # efface le port

############################################
# Démarrage de l'outil de traçage interactif et
# tracé de 180 degrés avec des données factices pour commencer
############################################

fig = plt.figure(facecolor='k')
win = fig.canvas.manager.window  # fenêtre de la figure
screen_res = win.wm_maxsize()  # utilisé pour le formatage de la fenêtre plus tard
dpi = 200  # résolution de la figure
fig.set_dpi(dpi)  # définit la résolution de la figure

# attributs de tracé polaire et conditions initiales
ax = fig.add_subplot(111, polar=True, facecolor='#001400')  # Changer la couleur de fond ici (bleu foncé)
ax.set_position([-0.05, 0.05, 1.1, 1.05])
r_max = 100.0
ax.set_ylim([0.0, r_max])
ax.set_xlim([0.0, np.pi])
ax.tick_params(axis='both', colors='w')
ax.grid(color='w', alpha=0.2)  # Couleur de la grille (blanc avec alpha 0.2)
ax.set_rticks(np.linspace(0.0, r_max, 5))
ax.set_thetagrids(np.linspace(0.0, 180.0, 10))

angles = np.arange(0, 181, 1)  # 0 - 180 degrés
theta = angles * (np.pi / 180.0)  # en radians
dists = np.ones((len(angles),))  # distances factices jusqu'à ce que les vraies données arrivent
pols, = ax.plot([], linestyle='', marker='o', markerfacecolor='r',  # Changer la couleur du visage du marqueur (rouge)
                markeredgecolor='r', markeredgewidth=0.5,  # Changer la couleur et l'épaisseur du bord du marqueur (rouge avec bord plus fin)
                markersize=7.0, alpha=0.7)  # Transparence du marqueur (alpha 0.7 pour plus de transparence)
line1, = ax.plot([], color='w', linewidth=4.0)  # tracé du bras balayé

# ajustements de présentation de la figure
fig.set_size_inches(0.96 * (screen_res[0] / dpi), 0.96 * (screen_res[1] / dpi))
plot_res = fig.get_window_extent().bounds
win.wm_geometry('+{0:1.0f}+{1:1.0f}'.format((screen_res[0] / 2.0) - (plot_res[2] / 2.0),
                                            (screen_res[1] / 2.0) - (plot_res[3] / 2.0)))
win.wm_title('Arduino Radar')  # Changer le titre de la fenêtre (facultatif)

fig.canvas.draw()  # dessiner avant la boucle
axbackground = fig.canvas.copy_from_bbox(ax.bbox)  # arrière-plan à conserver pendant la boucle

# Ajustements de présentation de la figure
# Modify the size of the figure here (width, height) in inches
fig.set_size_inches(30, 6)  # Example: Set the figure size to 10 inches wide and 6 inches tall

# Modify the font size for axis labels and tick labels
font_size = 2  # Set the desired font size here
matplotlib.rcParams['axes.labelsize'] = font_size
matplotlib.rcParams['xtick.labelsize'] = font_size
matplotlib.rcParams['ytick.labelsize'] = font_size

############################################
# événement du bouton pour arrêter le programme
############################################

def stop_event(event):
    global stop_bool
    stop_bool = 1

prog_stop_ax = fig.add_axes([0.85, 0.025, 0.125, 0.05])
pstop = Button(prog_stop_ax, 'Arrêter ', color='#00000F', hovercolor='w')  # Changer la couleur du bouton en bleu (code hexadécimal pour le bleu)
pstop.on_clicked(stop_event)

# bouton pour fermer la fenêtre
def close_event(event):
    global stop_bool, close_bool
    if stop_bool:
        plt.close('all')
    stop_bool = 1
    close_bool = 1

close_ax = fig.add_axes([0.025, 0.025, 0.125, 0.05])
close_but = Button(close_ax, 'Fermer ', color='#00000F', hovercolor='w')  # Changer la couleur du bouton en bleu (code hexadécimal pour le bleu)
close_but.on_clicked(close_event)

fig.show()

############################################
# boucle infinie, mise à jour constante du radar
# de 180 degrés avec les données entrantes de l'Arduino
############################################

start_word, stop_bool, close_bool = False, False, False
while True:
    try:
        if stop_bool:  # arrête le programme
            fig.canvas.toolbar.pack_configure()  # afficher la barre d'outils
            if close_bool:  # ferme la fenêtre du radar
                plt.close('all')
            break
        ser_bytes = ser.readline()  # lire les données série de l'Arduino
        decoded_bytes = ser_bytes.decode('utf-8')  # décode les données en utf-8
        data = (decoded_bytes.replace('\r', '')).replace('\n', '')
        if start_word:
            vals = [float(ii) for ii in data.split(',')]
            print(vals)
            if len(vals) < 2:
                continue
            angle, dist = vals  # séparer l'angle et la distance
            if dist > r_max:
                dist = 0.0  # mesurant plus que r_max, c'est probablement inexact
            dists[int(angle)] = dist
            if angle % 5 == 0:  # mise à jour tous les 5 degrés
                pols.set_data(theta, dists)
                fig.canvas.restore_region(axbackground)
                ax.draw_artist(pols)

                line1.set_data(np.repeat((angle * (np.pi / 180.0)), 2),
                               np.linspace(0.0, r_max, 2))
                ax.draw_artist(line1)

                fig.canvas.blit(ax.bbox)  # retrace uniquement les données
                fig.canvas.flush_events()  # vidage pour le tracé suivant
        else:
            if data == 'Radar Start':  # mot de départ sur l'Arduino
                start_word = True  # attendre que l'Arduino affiche le mot de départ
                print('Démarrage du radar...')
            else:
                continue

    except KeyboardInterrupt:
        plt.close('all')
        print('Interruption clavier')
        break
