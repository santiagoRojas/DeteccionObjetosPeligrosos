from __future__ import division
from modelos import *
from utils.utils import *
from utils.datasets import *
import os
import sys
import argparse
import cv2
from PIL import Image
import torch
from torch.autograd import Variable


#combierte la imagen a RGB
def Convertir_RGB(img):
    # Convertir Blue, green, red a Red, green, blue
    b = img[:, :, 0].copy()
    g = img[:, :, 1].copy()
    r = img[:, :, 2].copy()
    img[:, :, 0] = r
    img[:, :, 1] = g
    img[:, :, 2] = b
    return img

#combierte la imagen a BGR
def Convertir_BGR(img):
    # Convertir red, blue, green a Blue, green, red
    r = img[:, :, 0].copy()
    g = img[:, :, 1].copy()
    b = img[:, :, 2].copy()
    img[:, :, 0] = b
    img[:, :, 1] = g
    img[:, :, 2] = r
    return img



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--modelo", type=str, default="configuracion/yolov3.cfg", help="ruta al archivo de definición del modelo ")
    parser.add_argument("--ruta_pesos", type=str, default="pesos/checkpoint.pth", help="ruta al archivo de pesos")
    parser.add_argument("--ruta_nombre_clases", type=str, default="datos/clases.names", help="ruta al archivo de etiqueta de clase")
    parser.add_argument("--umbral_confianza", type=float, default=0.8, help="umbral de confianza del objeto")
    parser.add_argument("--webcam", type=int, default=1,  help="se utilizara una webcam 1 = Sí, 0 = no" )
    parser.add_argument("--umbral_iou", type=float, default=0.4, help="umbral de iou para supresión no máxima")
    parser.add_argument("--tamanio_cada_imagen", type=int, default=416, help="tamaño de cada dimensión de la imagen")
    parser.add_argument("--directorio_video", type=str, help="Directorio del video para la deteccion")
    parametros = parser.parse_args()
    #mostramos los parametros descritos por el usuario
    print(parametros)
    #se valida si el sistema posee targeta grafica nvidia para trabajar con cuda de lo contrario solo CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("cuda" if torch.cuda.is_available() else "cpu")
    #carga el modelo con los parametros dados por el usuario, el cual es YOLOv3 presonalizado segun la necesidad para n clases
    model = Darknet(parametros.modelo, img_size=parametros.tamanio_cada_imagen).to(device)

    #se pregunta si los pesos envidados son los que por defecto otroga Darknet o son de un entrenamiento personalizado
    #los pesos por default tienen una extencion .weights
    if parametros.ruta_pesos.endswith(".weights"):
        model.load_darknet_weights(parametros.ruta_pesos)
    else:
    #los pesos personalizados de entrenamiento tienen una extencion de .pth
        model.load_state_dict(torch.load(parametros.ruta_pesos))

    model.eval()
    #se cargan los nombres de las clases(objetos) que se desea que se detecte
    classes = load_classes(parametros.ruta_nombre_clases)
    Tensor = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor
    #se carga el tipo de video dependiendo de la opcion del usuario, si es 1 es la webcam de la maquina, de lo contrario un video con la ruta dada
    if parametros.webcam==1:
        #llama al metodo VideoCapture de la libreria openCV con el parametro 0 para lectura de webcam
        cap = cv2.VideoCapture(0)
        #guarda un archivo .mp4(video) donde se encuentran los resultados de la detección
        out = cv2.VideoWriter('videowebcamSalida.mp4',cv2.VideoWriter_fourcc('M','J','P','G'), 10, (1280,960))
    else:
        #llama al metodo VideoCapture de la libreria openCV y envia como parametro la ruta del video que se desea detectar
        cap = cv2.VideoCapture(parametros.directorio_video)
        #guarda un archivo .mp4(video) donde se encuentran los resultados de la detección
        out = cv2.VideoWriter('videoDeteccionSalida.mp4',cv2.VideoWriter_fourcc('M','J','P','G'), 10, (1280,960))
    #se le asigna un color random a los cuadros que encerrarán las detecciones
    colors = np.random.randint(0, 255, size=(len(classes), 3), dtype="uint8")

    a=[]
    #mientras este capturando sea el video o la webcam continua ennn el ciclo
    while cap:
        #lee la captura de video o webcam
        ret, frame = cap.read()
        if ret is False:
            break
        frame = cv2.resize(frame, (1280, 960), interpolation=cv2.INTER_CUBIC)

        #LA imagen viene en Blue, Green, Red y la convertimos a RGB que es la entrada que requiere el modelo
        RGBimg=Convertir_RGB(frame)
        imgTensor = transforms.ToTensor()(RGBimg)
        imgTensor, _ = pad_to_square(imgTensor, 0)
        imgTensor = resize(imgTensor, 416)
        imgTensor = imgTensor.unsqueeze(0)
        imgTensor = Variable(imgTensor.type(Tensor))

        #recoge las detecciones que se encontraron
        with torch.no_grad():
            detections = model(imgTensor)
            detections = non_max_suppression(detections, parametros.umbral_confianza, parametros.umbral_iou)

        #cada una de las detecciones debe ser dibjada en el frame
        for detection in detections:
            if detection is not None:

                detection = rescale_boxes(detection, parametros.tamanio_cada_imagen, RGBimg.shape[:2])

                for x1, y1, x2, y2, conf, cls_conf, cls_pred in detection:
                    box_w = x2 - x1
                    box_h = y2 - y1
                    color = [int(c) for c in colors[int(cls_pred)]]
                    #se imprime por consola la ubicación de la detección detección
                    print("Se detectó {} en X1: {}, Y1: {}, X2: {}, Y2: {}".format(classes[int(cls_pred)], x1, y1, x2, y2))
                    #se dibuja el cuadro de detección en el frame
                    frame = cv2.rectangle(frame, (x1, y1 + box_h), (x2, y1), color, 5)
                    cv2.putText(frame, classes[int(cls_pred)], (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 5)# Nombre de la clase detectada
                    cv2.putText(frame, str("%.2f" % float(conf)), (x2, y2 - box_h), cv2.FONT_HERSHEY_SIMPLEX, 0.5,color, 5) # Certeza de prediccion de la clase

        #Se Converte de vuelta a BGR para que cv2 pueda desplegarlo en los colores correctos
        #si es en webcam este procemimiento es diferente que con un video
        if parametros.webcam==1:
            cv2.imshow('frame', Convertir_BGR(RGBimg))
            out.write(RGBimg)
        else:
            out.write(Convertir_BGR(RGBimg))
            cv2.imshow('frame', RGBimg)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    #se libera el out, la captura y destruye la ventana de opencv donde se estaban mostrando los resulatados
    out.release()
    cap.release()
    cv2.destroyAllWindows()