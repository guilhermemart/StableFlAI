import torch
import torchvision
import cv2
import numpy as np
from PIL import ImageGrab
import time
from random import randrange as rand
from pathlib import Path
import service
from torchvision.models.detection.ssd import SSDClassificationHead
from torchvision.models.detection import _utils


if __name__ == '__main__':

    # Carregar o modelo SSD pré-treinado
    if Path(__file__).parent.joinpath('model.pt').exists():
        model = torch.load('model.pt')
    else: 
        model = torchvision.models.detection.ssd300_vgg16(weights='COCO_V1')

    # Carregar o modelo SSD personalizado
    if Path(__file__).parent.joinpath('model_local.pt').exists():
        model_local = torch.load('model_local.pt')
    else: 
        size = 600
        num_classes=2
        model_local = torchvision.models.detection.ssd300_vgg16(weights="COCO_V1")
        # Retrieve the list of input channels. 
        in_channels = _utils.retrieve_out_channels(model_local.backbone, (size, size))
        # List containing number of anchors based on aspect ratios.
        num_anchors = model_local.anchor_generator.num_anchors_per_location()
        # The classification head.
        model_local.head.classification_head = SSDClassificationHead(
            in_channels=in_channels,
            num_anchors=num_anchors,
            num_classes=2,
        )
        # Image size for transforms.
        model_local.transform.min_size = (size,)
        model_local.transform.max_size = size

    # Treinar o model COCO para imagens locais
    path = Path(__file__).parent.joinpath('data')
    model = service.train(model, str(path.joinpath('person').absolute()), 0)

    # Treinar o model local para imagens heads
    model_local = service.train(model_local, str(path.joinpath('head').absolute()), 20)
    
    # Capturar um print do monitor
    printScreen = ImageGrab.grab()
    # Converter o print de BGR para RGB e já transformar em um array numpy
    printScreen = cv2.cvtColor(np.array(printScreen), cv2.COLOR_BGR2RGB)

    # Transformar a imagem em um tensor
    image_tensor = service.transform(printScreen)

    # Fazer a predição com o modelo SSD
    with torch.no_grad():
        model.eval()
        output = model(image_tensor)
        model_local.eval()
        output_local = model_local(image_tensor)

    # Extrair as caixas delimitadoras, os rótulos e os escores da saída do modelo
    boxes = output[0]['boxes'].int().numpy()
    labels = output[0]['labels'].numpy()
    scores = output[0]['scores'].numpy()

    # Desenhar as caixas delimitadoras na imagem original
    # Se houver pessoa preenche x
    _, x = service.untransform_and_draw_boxes(image_tensor[0], boxes, labels, scores, threshold=0.5, save_as='person')
    print(f"Persons: {len(x)}")

        
    boxes_local = output_local[0]['boxes'].int().numpy()
    labels_local = output_local[0]['labels'].numpy()
    scores_local = output_local[0]['scores'].numpy()
    
    print(f'Detections: {len(labels)}')

    image_with_boxes, x = service.untransform_and_draw_boxes(image_tensor[0], boxes_local, labels_local, scores_local, threshold=0.1, save_as='head')
    print(f"Heads: {len(x)}")

    # salvar a imagem com as caixas delimitadoras
    # cv2.imshow('Image with boxes',  image_with_boxes)
    cv2.imwrite('Image_with_boxes.jpeg', image_with_boxes, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    #save the models
    torch.save(model, 'model.pt')
    torch.save(model_local, 'model_local.pt')
