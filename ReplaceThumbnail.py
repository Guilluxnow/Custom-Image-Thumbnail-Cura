# Copyright (c) 2025 Guillaume Moruno
# Email: gui.moruno@gmail.com
# Version: 2.0
import base64
import os
from UM.Logger import Logger
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QBuffer, QIODevice, Qt

from ..Script import Script

def getMetaData():
    return {}

class ReplaceThumbnail(Script):
    def __init__(self):
        super().__init__()

    def _loadImageFromFile(self, image_path, target_width, target_height):
        if not image_path or not os.path.exists(image_path):
            Logger.log("w", f"Chemin de l'image invalide ou fichier non trouvé : {image_path}")
            return None, 0, 0
        try:
            image = QImage(image_path)
            if image.isNull():
                Logger.log("w", f"Échec du chargement de l'image depuis {image_path}")
                return None, 0, 0
            scaled_image = image.scaled(target_width, target_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return scaled_image, scaled_image.width(), scaled_image.height()
        except Exception as e:
            Logger.logException("w", f"Erreur lors du traitement de l'image : {e}")
            return None, 0, 0

    def _encodeImage(self, image):
        try:
            thumbnail_buffer = QBuffer()
            thumbnail_buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            image.save(thumbnail_buffer, "PNG")
            base64_bytes = base64.b64encode(thumbnail_buffer.data())
            base64_message = base64_bytes.decode('ascii')
            thumbnail_buffer.close()
            return base64_message
        except Exception:
            Logger.logException("w", "Échec de l'encodage de l'image en Base64")
            return None

    def _convertImageToGcode(self, encoded_image, width, height, chunk_size=78):
        gcode = [";"]
        gcode.append(f"; thumbnail begin {width}x{height} {len(encoded_image)}")
        gcode.extend([f"; {encoded_image[i:i+chunk_size]}" for i in range(0, len(encoded_image), chunk_size)])
        gcode.append("; thumbnail end")
        gcode.append(";")
        return gcode

    def getSettingDataString(self):
        return """{
            "name": "Miniature Personnalisée (Klipper & Mooracker)",
            "key": "ReplaceThumbnail",
            "metadata": {},
            "version": 2,
            "settings": {
                "image_path": {
                    "label": "Chemin de l'image",
                    "description": "Chemin complet vers l'image. Utilisez des slashes '/', même sur Windows. Ex: C:/Images/mon_image.png",
                    "type": "str",
                    "default_value": ""
                },
                "target_width": {
                    "label": "Largeur de la miniature (px)",
                    "description": "La largeur cible pour la miniature. L'image gardera ses proportions.",
                    "type": "int",
                    "default_value": 300
                },
                "target_height": {
                    "label": "Hauteur de la miniature (px)",
                    "description": "La hauteur cible pour la miniature. L'image gardera ses proportions.",
                    "type": "int",
                    "default_value": 300
                }
            }
        }"""

    def execute(self, data):
        image_path = self.getSettingValueByKey("image_path")
        if not image_path:
            Logger.log("i", "Aucun chemin d'image spécifié, le script est ignoré.")
            return data

        target_width = self.getSettingValueByKey("target_width")
        target_height = self.getSettingValueByKey("target_height")

        image, width, height = self._loadImageFromFile(image_path, target_width, target_height)
        if not image:
            return data

        encoded_image = self._encodeImage(image)
        if not encoded_image:
            return data

        image_gcode = self._convertImageToGcode(encoded_image, width, height)
        
        for i, layer_gcode in enumerate(data):
            lines = layer_gcode.split("\n")
            for j, line in enumerate(lines):
                if line.startswith(";LAYER_COUNT:"):
                    lines[j+1:j+1] = image_gcode
                    data[i] = "\n".join(lines)
                    Logger.log("i", f"Miniature personnalisée '{os.path.basename(image_path)}' insérée avec succès.")
                    return data
        
        Logger.log("w", "Le point d'insertion ';LAYER_COUNT:' n'a pas été trouvé. La miniature n'a pas été ajoutée.")
        return data