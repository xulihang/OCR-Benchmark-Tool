import json
import argparse
import os
import conf
import editdistance
from passporteye.mrz.text import MRZ
from aggregated_reader import AggregatedReader

engines = conf.engines
parser = argparse.ArgumentParser()
parser.add_argument("--path", help="path of data.json")
parser.add_argument("--engine", help="engine name")
parser.add_argument("--calculate", help="calculate score only (pass any value to enable)")
parser.add_argument("--enabled_engines", help="enabled engines list")
args = parser.parse_args()


def load_engines(conf_path):
    global engines
    engines = []
    with open(conf_path,"r") as f:
        for line in f.readlines():
            engines.append(line.strip())

def read_images_data(path):
    with open(path,"r") as f:
        images = json.loads(f.read())["images"]
    return images
    
def ocr_and_save_result(reader, image):
    filename = image["filename"]
    full_path = os.path.join(os.getcwd(), filename)
    result_dict = reader.ocr(full_path)
    engine = reader.engine
    
    print(result_dict)
    print("done")
    result_dict["valid_score"] = get_valid_score(result_dict["boxes"])
    result_dict["score"] = get_similarity(get_total_text_of_boxes(result_dict["boxes"]), get_total_text_of_boxes(image["boxes"]))
    
    output_path = get_engine_json_name(filename, engine)
    print(output_path)
    with open(output_path, "w") as f:
        f.write(json.dumps(result_dict))

def get_engine_json_name(filename, engine):
    name, ext = os.path.splitext(filename)
    return name + "-" + engine + ".json"

def save_overall_statistics(overall_scores, details):
    with open("statistics.json","w") as f:
        f.write(json.dumps(overall_scores))
    with open("details.json","w") as f:
        f.write(json.dumps(details))

def get_overall_statistics(images):
    engines_score_of_images = {}
    overall_scores = {}
    for engine in engines:
        engine_result = {}
        total_score = 0
        total_valid_score = 0
        total_time = 0
        exact_num = 0
        for image in images:
            result_dict = get_ocr_result_dict_from_json(engine, image)
            ocr_result = get_total_text_of_boxes(result_dict["boxes"])
            ground_truth = get_total_text_of_boxes(image["boxes"])
            score = get_similarity(ocr_result, ground_truth)
            
            if int(score) == 1:
                exact_num = exact_num + 1
            
            valid_score = get_valid_score(result_dict["boxes"])
           
            engines_score_of_images[engine+image["filename"]] = score
            
            total_score = total_score + score
            total_valid_score = total_valid_score + valid_score
            total_time = total_time + result_dict["elapsedTime"]
        engine_result["valid_score"] = total_valid_score/len(images)
        engine_result["score"] = total_score/len(images)
        engine_result["exact_num"] = exact_num
        engine_result["exact_rate"] = exact_num/len(images)
        engine_result["total_time"] = total_time
        engine_result["average_time"] = total_time/len(images)
        overall_scores[engine] = engine_result
        
    details = {}
    for image in images:
        image_dict = {}
        engines_dict = {}
        for engine in engines:
            engine_dict = {}
            engine_dict["score"] = engines_score_of_images[engine+image["filename"]]
            result_dict = get_ocr_result_dict_from_json(engine, image)
            ocr_result = get_total_text_of_boxes(result_dict["boxes"])
            engine_dict["ocr_result"] = ocr_result
            engine_dict["valid_score"] = get_valid_score(result_dict["boxes"])
            engines_dict[engine] = engine_dict
        ground_truth = get_total_text_of_boxes(image["boxes"])
        image_dict["engines"] = engines_dict
        image_dict["ground_truth"] = ground_truth
        details[image["filename"]] = image_dict
    return overall_scores, details

def get_ocr_result_dict_from_json(engine, image):
    json_name = get_engine_json_name(image["filename"], engine)
    with open(json_name, "r") as f:
        result_dict = json.loads(f.read())
        return result_dict
    
def get_total_text_of_boxes(boxes):
    text = ""
    for box in boxes:
        text = text + box["text"] + "\n"
    return text.strip()

def get_similarity(text, ground_truth):
    distance = editdistance.eval(text, ground_truth)
    return 1 - distance/max(len(text),len(ground_truth))
    
def get_valid_score(boxes):
    lines = []
    for box in boxes:
        text = box["text"]
        for line in text.split("\n"):
            lines.append(line)
    m = MRZ(lines)
    return m.valid_score

def ocr_all_images(images):
    for engine in engines:
        reader = AggregatedReader(engine)
        for image in images:
            print("OCRing:")
            print(image)
            ocr_and_save_result(reader, image)
        
def run():
    if args.engine:
        global engines
        engines = []
        engines.append(args.engine)
    else:
        if args.enabled_engines:
            load_engines(args.enabled_engines)
    if os.path.exists(args.path) == False:
        print("path does not exist")
        return
    parent_path = os.path.abspath(os.path.dirname(args.path))
    print(parent_path)
    os.chdir(parent_path)
    images = read_images_data(args.path)
    
    if args.calculate:
        overall_scores, details = get_overall_statistics(images)
        save_overall_statistics(overall_scores, details)
    else:
        ocr_all_images(images)
    
run()
    
    
    