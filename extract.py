import sys
from svgelements import *
import xml.etree.ElementTree as ET

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

add_pixels = 8
clefLineLoc = {
    'treble': {
        'A3': 19, 'B3': 20, 'C4': 21, 'D4': 22, 'E4': 23, 'F4': 24, 'G4': 25,
        'A4': 26, 'B4': 27, 'C5': 28, 'D5': 29, 'E5': 30, 'F5': 31, 'G5': 32, 'A5': 33, 'B5': 34, 'C6': 35
    },
    'bass': {
        'C2': 19, 'D2': 20, 'E2': 21, 'F2': 22, 'G2': 23, 'A2': 24, 'B2': 25,
        'C3': 26, 'D3': 27, 'E3': 28, 'F3': 29, 'G3': 30, 'A3': 31, 'B3': 32, 'C4': 33, 'D4': 34, 'E4': 35
    },
    'alto': {
        'B2': 19, 'C3': 20, 'D3': 21, 'E3': 22, 'F3': 23, 'G3': 24, 'A3': 25,
        'B3': 26, 'C4': 27, 'D4': 28, 'E4': 29, 'F4': 30, 'G4': 31, 'A4': 32, 'B4': 33, 'C5': 34, 'D5': 35
    }
}

WHOLE = 10
HALF_DOT = 11
HALF = 12
QUARTER_DOT = 13
QUARTER = 14
EIGHTH_DOT = 15
EIGHTH = 16
SIXTEEN = 17
THIRTYTWO = 18

sharp_id = 0
flat_id = 1
natural_id = 2
gclef_id = 3
fclef_id = 4
cclef_id = 5
barline_id = 6
timesig_id = 7
notes_id = 8
rests_id = 9

ACCIDENTAL = {'sharp': sharp_id,
              'flat': flat_id,
              'natural': natural_id}


class StaffSystem:
    def __init__(self, y):
        self.y = y
        self.notes = list()
        self.dots = list()
        self.stems = list()
        self.hooks = list()
        self.rests = list()
        self.clefs = list()
        self.timesigs = list()
        self.keysigs = list()
        self.accidentals = list()


def bbox_to_rect(bbox, color):
    x = bbox[0]
    y = bbox[1]
    w = bbox[2] - x
    h = bbox[3] - y
    box = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" style="stroke: {color}; fill: none"/>'
    return f'{box}\n'


def bbox_to_coco(bbox, classification):
    return f'{classification} {bbox[0]} {bbox[1]} {bbox[2] - bbox[0]} {bbox[3] - bbox[1]}'


def bbox_to_pascal_voc(bbox, classification):
    return f'{classification} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}'


def bbox_to_choice(bbox, classification):
    toText = True
    if toText:
        return f'{bbox_to_coco(bbox, classification)}\n'
    else:
        if classification in (fclef_id, gclef_id, cclef_id):
            return bbox_to_rect(bbox, '#1FDEDE')
        elif classification == barline_id:
            return bbox_to_rect(bbox, '#F2F600')
        elif classification == notes_id:
            return bbox_to_rect(bbox, '#DE1F1F')
        elif classification == rests_id:
            return bbox_to_rect(bbox, '#8AFF00')
        elif classification in (sharp_id, flat_id, natural_id):
            return bbox_to_rect(bbox, '#FFA200')
        elif classification == timesig_id:
            return bbox_to_rect(bbox, '#005DFF')


def write_svg(boxes, svg):
    with open(svg, 'r') as f:
        data = f.readlines()
    close_tag = data.pop(len(data) - 1)
    data.append(boxes)
    data.append(close_tag)
    with open(svg.replace('.svg', '_boxes.svg'), 'w') as f:
        f.writelines(data)


def get_staff_system_index(element, systems):
    element_y = element.bbox()[1]
    min_dist = sys.maxsize
    min_index = 0
    for i in range(len(systems)):
        dist = abs(element_y - systems[i].y)
        if dist < min_dist:
            min_dist = dist
            min_index = i
    return min_index


def sort_after_x(element):
    return element.bbox()[0]


def prepare_barline(barline):
    stroke_width = barline.values.get('stroke-width')
    barline_bbox = barline.bbox()
    stroke_half_width = float(stroke_width) / 2
    barline += SimpleLine(barline_bbox[0], barline_bbox[1], barline_bbox[0] - stroke_half_width, barline_bbox[1])
    barline += SimpleLine(barline_bbox[2], barline_bbox[3], barline_bbox[2] + stroke_half_width, barline_bbox[3])
    return barline


def determine_clef(clef):
    if clef == 'treble':
        return gclef_id
    elif clef == 'bass':
        return fclef_id
    elif clef == 'alto':
        return cclef_id


def rest_duration(note):
    if note.find('rest').get('measure') == 'yes':
        return WHOLE
    else:
        return note_duration(note)


def note_duration(note):
    type = note.findtext('type')
    dot = note.find('dot')
    if type == 'whole':
        return WHOLE
    elif type == 'half':
        if dot is not None:
            return HALF_DOT
        return HALF
    elif type == 'quarter':
        if dot is not None:
            return QUARTER_DOT
        return QUARTER
    elif type == 'eighth':
        if dot is not None:
            return EIGHTH_DOT
        return EIGHTH
    elif type == '16th':
        return SIXTEEN
    elif type == '32nd':
        return THIRTYTWO
    else:
        raise Exception('unsupported duration')


def staffline(note):
    step = note.findtext('pitch/step')
    octave = note.findtext('pitch/octave')
    return f'{step}{octave}'


def signline_to_clef(clef):
    sign = clef.findtext('sign')
    line = clef.findtext('line')
    if f'{sign}{line}' == 'G2':
        return 'treble'
    elif f'{sign}{line}' == 'F4':
        return 'bass'
    elif f'{sign}{line}' == 'C3':
        return 'alto'
    else:
        raise Exception('not supported clef')


def keysign(lastKey, key):
    alter = int(key.findtext('fifths'))
    if lastKey is None and alter == 0:
        return None
    return alter


def timesign(time):
    if time.get('symbol') is not None:
        raise Exception('unsupported time symbol')
    beats = time.findtext('beats')
    beat_type = time.findtext('beat-type')
    return f'{beats}/{beat_type}'


def determine_accidental(accidental):
    accidental_id = ACCIDENTAL[accidental]
    if accidental_id is None:
        raise Exception('unsupported accidental')
    return accidental_id


def has_stem(note):
    stems = note.findall('stem')
    if len(stems) > 1:
        raise Exception('unsupported amount of stems')
    return len(stems) == 1


def has_dot(note):
    dots = note.findall('dot')
    if len(dots) > 1:
        raise Exception('unsupported amount of dots')
    return len(dots) == 1


def has_hook(note, duration):
    hasNoBeams = note.find('beam') is None
    return duration in (THIRTYTWO, SIXTEEN, EIGHTH, EIGHTH_DOT) and hasNoBeams


def has_beams(note):
    beams = [beam.text for beam in note.findall('beam')]
    if len(beams) == 0:
        return 0
    stemDirection = note.findtext('stem')
    category = 0
    if 'continue' in beams or ('begin' in beams and 'end' in beams):
        category = 2
    elif 'begin' in beams:
        category = 1
    elif 'end' in beams:
        category = 3
    else:
        raise Exception('unsupported beam configuration')
    if stemDirection == 'up':
        return category * 1
    elif stemDirection == 'down':
        return category * -1
    else:
        raise Exception('unsupported stem configuration')


class Score:
    def __init__(self):
        self.svgAccidentals = list()
        self.svgKeysigs = list()
        self.svgClefs = list()
        self.svgRests = list()
        self.svgTimesigs = list()
        self.svgBarlines = list()
        self.svgNotes = list()
        self.svgStems = list()
        self.svgHooks = list()
        self.svgNoteDots = list()

        self.svgAccidentalsIter = None
        self.svgKeysigsIter = None
        self.svgClefsIter = None
        self.svgRestsIter = None
        self.svgTimesigsIter = None
        self.svgNotesIter = None
        self.svgStemsIter = None
        self.svgHooksIter = None
        self.svgNoteDotsIter = None

        self.lastClef = None
        self.lastKeySign = None
        self.lastTimeSign = None
        self.lastNote = None
        self.currentClef = clefLineLoc['treble']

        self.coords_and_classes = ''

    def classify(self, svg_file, musicxml_file):
        svg = SVG.parse(svg_file)
        linesIndex = 0
        staffLines = None
        systems = list()

        # create staff systems
        for element in svg.elements():
            classType = element.values.get('class')
            if classType == 'StaffLines':
                if linesIndex == 0:
                    staffLines = element
                    linesIndex += 1
                elif linesIndex == 4:
                    staffLines += element
                    linesIndex = 0
                    systems.append(
                        StaffSystem((staffLines.bbox()[3] - staffLines.bbox()[1]) / 2 + staffLines.bbox()[1]))
                else:
                    staffLines += element
                    linesIndex += 1

        # classify elements in svg
        for element in svg.elements():
            classType = element.values.get('class')
            if classType == 'Note':
                systems[get_staff_system_index(element, systems)].notes.append(element)
            elif classType == 'Rest':
                systems[get_staff_system_index(element, systems)].rests.append(element)
            elif classType == 'TimeSig':
                systems[get_staff_system_index(element, systems)].timesigs.append(element)
            elif classType == 'KeySig':
                systems[get_staff_system_index(element, systems)].keysigs.append(element)
            elif classType == 'Clef':
                systems[get_staff_system_index(element, systems)].clefs.append(element)
            elif classType == 'BarLine':
                if element.values.get('stroke-width') is not None:
                    self.svgBarlines.append(element)
            elif classType == 'Accidental':
                systems[get_staff_system_index(element, systems)].accidentals.append(element)
            elif classType == 'Stem':
                systems[get_staff_system_index(element, systems)].stems.append(element)
            elif classType == 'Hook':
                systems[get_staff_system_index(element, systems)].hooks.append(element)
            elif classType == 'NoteDot':
                systems[get_staff_system_index(element, systems)].dots.append(element)

        # sort elements where sorting is required
        for system in systems:
            self.svgNotes.extend(sorted(system.notes, key=sort_after_x))
            self.svgNoteDots.extend(sorted(system.dots, key=sort_after_x))
            self.svgStems.extend(sorted(system.stems, key=sort_after_x))
            self.svgHooks.extend(sorted(system.hooks, key=sort_after_x))
            self.svgRests.extend(sorted(system.rests, key=sort_after_x))
            self.svgClefs.extend(sorted(system.clefs, key=sort_after_x))
            self.svgTimesigs.extend(sorted(system.timesigs, key=sort_after_x))
            self.svgKeysigs.extend(sorted(system.keysigs, key=sort_after_x))
            self.svgAccidentals.extend(sorted(system.accidentals, key=sort_after_x))

        self.svgAccidentalsIter = iter(self.svgAccidentals)
        self.svgKeysigsIter = iter(self.svgKeysigs)
        self.svgClefsIter = iter(self.svgClefs)
        self.svgRestsIter = iter(self.svgRests)
        self.svgTimesigsIter = iter(self.svgTimesigs)
        self.svgNotesIter = iter(self.svgNotes)
        self.svgStemsIter = iter(self.svgStems)
        self.svgHooksIter = iter(self.svgHooks)
        self.svgNoteDotsIter = iter(self.svgNoteDots)

        for barline in self.svgBarlines:
            self.coords_and_classes += bbox_to_choice(prepare_barline(barline).bbox(), barline_id)

        scoreTree = ET.parse(musicxml_file)
        part = scoreTree.getroot().find('part')
        measures = part.findall('measure')

        for measure in measures:
            notes_rests = measure.findall('note')
            attributes = measure.findall('attributes')

            measure_clef = None
            measure_key = None
            lineStart = measure.find('print')
            isNewSystem = lineStart and lineStart.get('new-system')

            for attribute in attributes:
                if attribute.find('clef'):
                    measure_clef = signline_to_clef(attribute.find("clef"))
                    self.set_clef(measure_clef)
                    if isNewSystem:
                        self.add_clef()
                if attribute.find('key'):
                    measure_key = keysign(self.lastKeySign, attribute.find("key"))
                    if lineStart is None and (self.lastKeySign > 0 > measure_key or self.lastKeySign < 0 < measure_key):
                        self.set_keysign(0)
                    self.set_keysign(measure_key)
                    if isNewSystem:
                        self.add_keysign()
                if attribute.find('time'):
                    self.set_timesign(timesign(attribute.find("time")))
                    if isNewSystem:
                        self.add_timesign()
                measure_style = attribute.find('measure-style')
                if measure_style is not None and measure_style.find('multiple-rest') is not None:
                    raise Exception('unsupported rest style')

            # check for repeating clef
            if measure_clef is None and isNewSystem:
                self.add_clef()
            # check for repeating keysignature
            if measure_key is None and isNewSystem:
                self.add_keysign()

            for note in notes_rests:
                if note.find('rest') is None:
                    duration = note_duration(note)
                    accidental = note.find('accidental')
                    if accidental is not None:
                        boxAccidental = next(self.svgAccidentalsIter)
                        self.coords_and_classes += bbox_to_choice(boxAccidental.bbox(),
                                                                  determine_accidental(accidental.text))
                    boxElement = next(self.svgNotesIter)
                    if has_stem(note):
                        boxElement += next(self.svgStemsIter)
                    beam_category = has_beams(note)
                    if beam_category != 0:
                        bbox = boxElement.bbox()
                        if beam_category in (1, 2):
                            boxElement += SimpleLine(bbox[2], bbox[3], bbox[2] + add_pixels, bbox[3])
                        elif beam_category in (-2, -3):
                            boxElement += SimpleLine(bbox[0] - add_pixels, bbox[1], bbox[0], bbox[1])
                        if beam_category < 0:
                            boxElement += SimpleLine(bbox[2], bbox[3], bbox[2], bbox[3] + add_pixels)
                        elif beam_category > 0:
                            boxElement += SimpleLine(bbox[0], bbox[1], bbox[0], bbox[1] - add_pixels)
                    if has_dot(note):
                        boxElement += next(self.svgNoteDotsIter)
                    if has_hook(note, duration):
                        boxElement += next(self.svgHooksIter)
                    self.coords_and_classes += bbox_to_choice(boxElement.bbox(), duration)
                    self.coords_and_classes += bbox_to_choice(boxElement.bbox(), clefLineLoc[self.lastClef][staffline(note)])
                    self.coords_and_classes += bbox_to_choice(boxElement.bbox(), notes_id)
                elif note.find('rest') is not None:
                    duration = rest_duration(note)
                    boxElement = next(self.svgRestsIter)
                    if has_dot(note):
                        boxElement += next(self.svgNoteDotsIter)
                    self.coords_and_classes += bbox_to_choice(boxElement.bbox(), duration)
                    self.coords_and_classes += bbox_to_choice(boxElement.bbox(), rests_id)
        # write_svg(self.coords_and_classes, svg_file)
        return self.coords_and_classes

    def add_clef(self):
        path = next(self.svgClefsIter)
        self.coords_and_classes += bbox_to_choice(path.bbox(), determine_clef(self.lastClef))

    def add_timesign(self):
        boxElement = next(self.svgTimesigsIter) + next(self.svgTimesigsIter)
        self.coords_and_classes += bbox_to_choice(boxElement.bbox(), timesig_id)

    def add_keysign(self):
        if self.lastKeySign is None:
            return
        elif self.lastKeySign > 0:
            for x in range(0, self.lastKeySign):
                path = next(self.svgKeysigsIter)
                self.coords_and_classes += bbox_to_choice(path.bbox(), sharp_id)
        elif self.lastKeySign < 0:
            for x in range(self.lastKeySign, 0):
                path = next(self.svgKeysigsIter)
                self.coords_and_classes += bbox_to_choice(path.bbox(), flat_id)
        elif self.lastKeySign == 0:
            path = next(self.svgKeysigsIter)
            self.coords_and_classes += bbox_to_choice(path.bbox(), natural_id)
            self.lastKeySign = None

    def set_clef(self, new_clef):
        self.lastClef = new_clef
        self.add_clef()

    def set_keysign(self, new_keysign):
        self.lastKeySign = new_keysign
        self.add_keysign()

    def set_timesign(self, new_timesign):
        self.lastTimeSign = new_timesign
        self.add_timesign()


if __name__ == '__main__':
    score = Score()
    print(score.classify('out_dev/21148.svg', 'out_dev/21148.musicxml'))
