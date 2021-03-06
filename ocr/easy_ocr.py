import easyocr
import os
import sys
sys.path.append("..")
import ocr.utils

class EasyOCRReader():
    def __init__(self):
        current_lang="en"
        root = os.path.dirname(__file__)
        self.reader = easyocr.Reader([current_lang],model_storage_directory=root)
        self.postprocessing = "mrz"
        
    def ocr(self, file_path):
        result_dict = {}
        result = self.reader.readtext(file_path)

        lines = []
        for line in result:
            new_line = {}
            new_line["text"] = line[1]
            index=1
            for coord in line[0]:
                new_line["x"+str(index)]=int(coord[0])
                new_line["y"+str(index)]=int(coord[1])
                index=index+1
            lines.append(new_line)
        result_dict["boxes"] = ocr.utils.postprocess(self.postprocessing, lines)
        result_dict["raw_boxes"] = lines
        return result_dict
        
if __name__ == "__main__":
    reader = EasyOCRReader()
    result_dict = reader.ocr("test.jpg")
    print(result_dict)