import sys
import os
import csv

try:
    import lxml
except:
    import pip
    try:
        pip.main(["install", "pip"])
    except:
        print("Run the script as an administrator")
        sys.exit(1)

from lxml import etree

kicadpcb_extension = ".kicad_pcb"
gerberset_extension = ".gerberset"
pos_extension = ".pos"
# -s for running this script from another script, will not do the "press any key" thing at the end with it
args = ("-s",)
path = [el for el in sys.argv[1:] if el not in args][-1]

gerberset_file = None
gerberset_files = []
while not gerberset_file:
    if os.path.isdir(path):
        gerberset_files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(gerberset_extension)]
        gerberset_file = gerberset_files[0]
    elif os.path.isfile(path):
        if os.path.isfile(path) and path.endswith(gerberset_extension):
            gerberset_file = path
            gerberset_files = [gerberset_file]
        else:
            path = os.path.split(path)[0]
    else:
        raise ValueError("what even is this {}".format(path))
        
with open(gerberset_file, 'r') as f:
    gerberset_xml = f.read()

gerberset_xml = gerberset_xml.encode('utf-8')
parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
root = etree.fromstring(gerberset_xml, parser=parser)

def get_kicadpcb_files(path):
    return [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(kicadpcb_extension)]


def locate_pos_file(path):
    # Two options:
    # 1) .pos file is in the same dir as gerbers
    # 2) .pos file is in the upper dir, and there's a kicad_pcb file there as well
    pos_files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(pos_extension)]
    if not pos_files:
        if get_kicadpcb_files(path):
            pass #print(".pos file not found and we're in the project root")
        else:
            #print("Going up from {}".format(path))
            path = os.path.split(path)[0]
            if get_kicadpcb_files(path):
                pos_files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(pos_extension)]
                if not pos_files:
                    return None
            else:
                #print("No kicad_pcb file found, staying safe and not locating the .pos file")
                return None
    if len(pos_files) > 1:
        print("More than 1 file found! {}".format(pos_files))
        pos_files = pos_files[:1]
        print("Using {} - improve heuristics if you want".format(pos_files[0]))
    pos_path = pos_files[0]
    return pos_path

gerber_folder_els = root.xpath(".//LoadedOutlines/string")
pos_files = {}
for el in gerber_folder_els:
    path = el.text
    pos_file = locate_pos_file(path)
    if pos_file:
        #print(pos_file)
        pos_files[path]= pos_file
    else:
        print(".pos file not found for {}".format(path))
#print(pos_files)

pos_file_data = {}

for path, pos_file in pos_files.items():
    with open(pos_file, 'r') as f:
        c = f.read()
    lines = [f.strip() for f in c.split("\n")]
    pos_file_contents = []
    for line in lines:
        if line.startswith("#") or not line:
            continue
        try:
            els = [el.strip(' ') for el in line.split(" ")]
            els = [el for el in els if el]
            ref, val, pkg, x, y, rot, side = els
        except Exception as e:
            print(e)
            print("Can't parse line: {}".format(repr(line)))
            continue            
        pos_file_contents.append(els)
    pos_file_data[pos_file] = pos_file_contents

pos_output_data = []

def add_pos_for_gerber(pos_file_dels, cx, cy, angle, i):
    output = []
    for els in pos_file_els:
        ref, val, pkg, x, y, rot, side = els
        ref = "{}-{}".format(ref, i)
        x, y = float(x), float(y)
        if angle == 0:
            # 15-1, 50-3 => 15-1, 50-3
            x, y = cx+x, cy+y
        elif angle == 90:
            # 15-1, 50-3 => 15+3, 50-1
            x, y = cx-y, cy+x
        elif angle == -90:
            x, y = cx+y, cy-x
        elif angle == 180:
            x, y = cx-x, cy-y
        rot = float(rot)+angle
        while rot>360:
            rot = rot-360
        output.append([ref, val, pkg, x, y, rot, side])
    return output

gerber_instances = root.xpath(".//GerberInstance")
for i, instance in enumerate(gerber_instances):
    is_generated = True if instance.xpath("Generated")[0] == "true" else False
    if is_generated:
        continue
    cx = float(instance.xpath("Center/X")[0].text)
    cy = float(instance.xpath("Center/Y")[0].text)
    angle = int(instance.xpath("Angle")[0].text)
    gerber_path = instance.xpath("GerberPath")[0].text
    if gerber_path in pos_files:
        pos_file = pos_files[gerber_path]
        pos_file_els = pos_file_data[pos_file]
        if angle not in (0, 90, -90, 180):
            print("Can't process gerber file at {}, angle {} - unsupported angle".format(gerber_path, angle))
            continue
        pos_output = add_pos_for_gerber(pos_file_els, cx, cy, angle, i+1)
        pos_output_data += pos_output
    else:
        print("No .pos file found for {}, ignoring".format(gerber_path))

basepath, filename = os.path.split(gerberset_file)
output_file = os.path.join(basepath, "{}.pos".format(filename.rsplit('.', 1)[0]))

with open(output_file, 'w') as f:
    # Need to fake these 4:
    f.write("### Module positions - created on 01/30/19 07:34:23 ###\n")
    f.write("### Printed by Pcbnew version kicad 4.0.7\n")
    f.write("## Unit = mm, Angle = deg.\n")
    # f.write("## Side : All\n") # LitePlacer glitching?
    f.write("# Output autogenerated by Paneliser2PnP script\n")
    # Faking this one as well, just in case:
    f.write("# Ref Val Package PosX PosY Rot Side\n")
    for data_entry in pos_output_data:
        els = [str(el) if not isinstance(el, float) else "{:.4f}".format(el) for el in data_entry]
        f.write("     ".join(els)+"\n")
    f.write("## End")

if "-s" not in sys.argv:
    print("")
    input("Finished, press any key to exit")