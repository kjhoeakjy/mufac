"""저작권이 끝난 클래식 주제 선율 라이브러리와 피아노 MP3 생성기.

곡마다 주제 선율(프레이즈 단위), 코드, 반주 패턴, 느낌을 적어 둔다.
render()가 노래 구성(전주·A·A 옥타브 위·B·A·후주)으로 피아노 MP3를 만들고,
lyric_plan()이 가사를 멜로디에 맞춰 쓰도록 구간별 음절 수를 알려준다.

선율은 악보를 보고 적은 것이 아니라 기억으로 적은 주제부라, 세부 음은 원곡과 다를 수 있다.
"""

from __future__ import annotations

import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
import yaml

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "classical"
MIDI_DIR = ASSETS / "midi"
PD_DIED_BEFORE = 1955   # 사후 70년 (한국·EU)
PD_YEAR_BEFORE = 1930   # 미국: 1930년 이전 출판

SR = 44100
NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d)$")
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
QUALITY = {
    "": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11),
    "dim": (0, 3, 6), "dim7": (0, 3, 6, 9), "sus4": (0, 5, 7), "sus2": (0, 2, 7), "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "aug": (0, 4, 8), "m7b5": (0, 3, 6, 10),
}

# ---------------------------------------------------------------- 라이브러리
# phrases: "음:박" 띄어쓰기. r은 쉼표. 박은 time 단위(대개 4분음표, 6/8·3/8은 8분음표).
# chords: 구간의 마디마다 코드 하나.
LIBRARY: list[dict] = [
    {
        "id": "canon", "name": "파헬벨 캐논", "composer": "요한 파헬벨", "year": "1680년경",
        "key": "D", "time": 4, "bpm": 62, "pattern": "arp8",
        "story": """1680년 무렵 뉘른베르크의 오르가니스트 파헬벨이 쓴 곡. 두 마디 베이스가 스물여덟 번 반복되는 위에 세 성부가 같은 선율을 두 마디 간격으로 따라 들어온다.
파헬벨은 1683년 흑사병으로 첫 아내와 갓난 아들을 한꺼번에 잃었다. 이 곡이 바흐의 형 요한 크리스토프의 결혼식(1694)을 위해 쓰였다는 설이 있으나 확실하지 않다.
200년 넘게 잊혔다가 1968년 파야르 실내악단의 녹음으로 되살아났고, 지금은 세상에서 가장 많이 결혼식에서 연주되는 곡이 되었다. 장례식에서도 자주 쓰인다.""",
        "themes": ['약속', '결혼', '변하지 않는 것', '반복되는 하루', '이별', '오래된 연인'],
        "feel": "같은 여덟 마디 화성이 끝없이 돌아오는 곡. 돌고 도는 시간, 변하지 않는 마음, 결혼과 이별 양쪽에 다 쓰인다. 담담하고 따뜻하다.",
        "sections": {
            "A": {  # 2분음표 주제
                "phrases": ["F#5:2 E5:2 D5:2 C#5:2 B4:2 A4:2 B4:2 C#5:2",
                            "D5:2 C#5:2 B4:2 A4:2 G4:2 F#4:2 G4:2 E4:2"],
                "chords": ["D", "A", "Bm", "F#m", "G", "D", "G", "A"],
            },
            "B": {  # 4분음표 변주
                "phrases": ["D5:1 F#4:1 A4:1 G4:1 F#4:1 D4:1 F#4:1 E4:1",
                            "D4:1 B3:1 D4:1 A4:1 G4:1 B4:1 A4:1 G4:1",
                            "F#4:1 D4:1 E4:1 C#5:1 D5:1 F#5:1 A5:1 A4:1",
                            "B4:1 G4:1 A4:1 F#4:1 D4:1 D5:1 D5:1 C#5:1"],
                "chords": ["D", "A", "Bm", "F#m", "G", "D", "G", "A"],
            },
        },
        "map": {"verse": "B", "chorus": "A", "bridge": "B"},
        "arrangement": ["intro", "B", "A", "B", "A+", "A+", "outro"],
    },
    {
        "id": "fur_elise", "name": "엘리제를 위하여", "composer": "루트비히 판 베토벤", "year": "1810년",
        "key": "Am", "time": 3, "bpm": 150, "pattern": "arp3",
        "story": """1810년 4월 27일 베토벤이 쓴 바가텔. 악보 첫머리의 "엘리제를 위하여"는 사실 "테레제를 위하여"를 잘못 읽은 것이라는 설이 유력하다. 테레제 말파티는 그해 베토벤이 청혼했다가 거절당한 제자다.
베토벤은 이 무렵 이미 청력을 거의 잃어 가고 있었다. 악보는 그가 죽고 40년이 지난 1867년에야 발견되어 출판됐고, 정작 받을 사람은 끝내 듣지 못했다.
닿지 못한 고백, 이름조차 잘못 전해진 마음의 노래.""",
        "themes": ['짝사랑', '보내지 못한 편지', '거절', '닿지 않는 마음', '이름'],
        "feel": "누구나 아는 첫 네 음. 망설이며 맴도는 마음, 보내지 못한 편지, 닿지 않는 사람. 빠른 음이 많아 가사는 짧은 말을 촘촘히.",
        "sections": {
            "A": {
                "phrases": ["E5:1 D#5:1 E5:1 D#5:1 E5:1 B4:1 D5:1 C5:1 A4:2 r:1 C4:1 E4:1 A4:1 B4:2 r:1 E4:1 G#4:1 B4:1 C5:2 r:1 E4:1",
                            "E5:1 D#5:1 E5:1 D#5:1 E5:1 B4:1 D5:1 C5:1 A4:2 r:1 C4:1 E4:1 A4:1 B4:2 r:1 E4:1 C5:1 B4:1 A4:3"],
                "chords": ["Am", "Am", "Am", "E", "E", "Am", "Am", "Am", "Am", "E", "E", "Am"],
            },
            "B": {
                "phrases": ["B4:1 C5:1 D5:1 E5:3 G4:1 F5:1 E5:1 D5:3",
                            "F4:1 E5:1 D5:1 C5:3 E4:1 D5:1 C5:1 B4:3"],
                "chords": ["C", "C", "G", "G", "Am", "Am", "E", "E"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "B"},
        "arrangement": ["intro", "A", "A+", "B", "A", "A+", "outro"],
    },
    {
        "id": "ode_to_joy", "name": "환희의 송가", "composer": "루트비히 판 베토벤", "year": "1824년",
        "key": "G", "time": 4, "bpm": 84, "pattern": "block",
        "story": """1824년 교향곡 9번 마지막 악장. 가사는 실러가 1785년에 쓴 시 「환희에 부쳐」로, "모든 사람은 형제가 되리라"는 구절이 중심이다. 베토벤은 20대부터 이 시를 곡으로 만들고 싶어 했고 30년 만에 완성했다.
초연 때 베토벤은 완전히 귀가 먹은 상태였다. 연주가 끝나고도 박수를 듣지 못해 등을 돌리고 서 있었고, 알토 가수가 그를 돌려세워 환호하는 청중을 보게 했다.
들리지 않는 사람이 쓴, 함께 부르자는 노래. 유럽연합의 공식 찬가이며 베를린 장벽이 무너진 1989년 성탄절에 "환희" 대신 "자유"로 바꿔 불렸다.""",
        "themes": ['함께', '다시 일어섬', '위로', '형제', '새해', '희망', '어른'],
        "feel": "단순한 음계로 된 세상에서 가장 유명한 선율. 함께 부르는 노래, 다시 일어서는 아침, 모두에게 건네는 위로. 느리게 치면 찬송처럼 담담하다.",
        "sections": {
            "A": {
                "phrases": ["B4:1 B4:1 C5:1 D5:1 D5:1 C5:1 B4:1 A4:1",
                            "G4:1 G4:1 A4:1 B4:1 B4:1.5 A4:0.5 A4:2",
                            "B4:1 B4:1 C5:1 D5:1 D5:1 C5:1 B4:1 A4:1",
                            "G4:1 G4:1 A4:1 B4:1 A4:1.5 G4:0.5 G4:2"],
                "chords": ["G", "D", "G", "D", "G", "D", "G", "D G"],
            },
            "B": {
                "phrases": ["A4:1 A4:1 B4:1 G4:1 A4:1 B4:0.5 C5:0.5 B4:1 G4:1",
                            "A4:1 B4:0.5 C5:0.5 B4:1 A4:1 G4:1 A4:1 D4:2"],
                "chords": ["D", "G", "D", "D"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "B"},
        "arrangement": ["intro", "A", "B", "A+", "A+", "outro"],
    },
    {
        "id": "jesu", "name": "예수, 인류 소망의 기쁨", "composer": "요한 제바스티안 바흐", "year": "1723년",
        "key": "G", "time": 3, "bpm": 72, "pattern": "waltz",
        "story": """1723년 라이프치히에서 쓴 칸타타 BWV 147의 마지막 합창. 바흐는 이해부터 매주 한 곡씩 예배용 칸타타를 써야 했다.
바흐는 스무 명의 자녀 중 열 명을 어려서 잃었고, 1720년에는 여행에서 돌아와 보니 첫 아내 마리아 바르바라가 이미 세상을 떠나 묻혀 있었다. 이 곡은 그 뒤 재혼한 안나 막달레나와 새 가정을 꾸리던 시기의 음악이다.
멈추지 않는 셋잇단음표 위에 찬송 선율이 길게 놓인다. 슬픔 위에서 계속되는 일상, 묵묵히 이어지는 사랑. 1926년 마이라 헤스의 피아노 편곡으로 세계에 알려졌고 2차 대전 중 런던 내셔널 갤러리 점심 연주회에서 폭격 속의 사람들을 위로했다.""",
        "themes": ['묵묵한 사랑', '일상', '가족', '버팀', '결혼', '신앙', '부모'],
        "feel": "쉬지 않고 흐르는 셋잇단음. 조용히 계속되는 하루, 묵묵한 사랑, 결혼식 입장. 밝지만 들뜨지 않는다.",
        "sections": {
            "A": {
                "phrases": ["G4:.333 A4:.333 B4:.333 D5:.333 C5:.333 C5:.333 E5:.333 D5:.333 D5:.333 G5:.333 F#5:.333 G5:.333 D5:.333 B4:.333 G4:.333 A4:.333 B4:.333 C5:.333",
                            "D5:.333 E5:.333 D5:.333 C5:.333 B4:.333 A4:.333 B4:.333 G4:.333 F#4:.333 G4:.333 A4:.333 D4:.333 F#4:.333 A4:.333 C5:.333 B4:.333 A4:.333 B4:.333"],
                "chords": ["G", "D", "Em", "D"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "A"},
        "arrangement": ["intro", "A", "A", "A+", "A", "A+", "outro"],
    },
    {
        "id": "brahms_lullaby", "name": "브람스 자장가", "composer": "요하네스 브람스", "year": "1868년",
        "key": "F", "time": 3, "bpm": 76, "pattern": "waltz",
        "story": """1868년 브람스가 쓴 「자장가」 Op.49-4. 함부르크 시절 합창단원이던 베르타 포루프스키가 둘째 아들을 낳자 선물로 보냈다. 젊은 날 브람스는 베르타를 좋아했고, 그때 베르타가 그에게 불러 주던 빈의 옛 노래 선율을 이 곡의 반주 속에 숨겨 두었다.
브람스는 "베르타가 아기에게 이 노래를 부르는 동안, 누군가 그녀에게 사랑 노래를 부르고 있는 셈"이라고 편지에 썼다. 그는 평생 결혼하지 않았다.
나를 재워 주던 사람에게, 이제 내가 부르는 노래. 세상에서 가장 많이 불린 자장가.""",
        "themes": ['엄마', '아기', '어린 시절', '재워 주던 사람', '오래된 마음', '밤'],
        "feel": "재워 주던 사람의 목소리. 어린 날의 방, 부모님, 이제는 내가 누군가를 재우는 밤. 느리고 둥글다.",
        "sections": {
            "A": {
                "phrases": ["A4:0.5 A4:0.5 C5:1.5 A4:0.5 A4:1 C5:2 A4:0.5 C5:0.5 F5:1 E5:1 D5:1 D5:1 C5:2",
                            "G4:0.5 A4:0.5 Bb4:2 G4:0.5 A4:0.5 Bb4:2 G4:0.5 Bb4:0.5 E5:1 D5:1 C5:1 E5:1 F5:2",
                            "F4:0.5 F4:0.5 F5:2 D5:0.5 Bb4:0.5 A4:2 F4:0.5 G4:0.5 A4:3",
                            "F4:0.5 F4:0.5 F5:2 D5:0.5 Bb4:0.5 A4:1 C5:1 Bb4:1 G4:1 F4:2"],
                "chords": ["F", "F", "C7", "C7", "F", "C7", "C7", "F", "F", "Bb", "F", "F", "Bb", "F C7", "F"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "A"},
        "arrangement": ["intro", "A", "A+", "A", "outro"],
    },
    {
        "id": "greensleeves", "name": "그린슬리브스", "composer": "영국 민요", "year": "16세기",
        "key": "Am", "time": 6, "bpm": 170, "pattern": "arp6",
        "story": """16세기 말 영국의 노래. 1580년에 「레이디 그린슬리브스」라는 제목으로 등록된 기록이 있다. 헨리 8세가 앤 불린을 위해 썼다는 이야기는 전설일 뿐 사실이 아니다.
가사는 사랑하는 여인에게 모든 것을 주었지만 버림받은 남자의 노래다. 원래 가사에는 그녀에게 사 준 옷과 보석 목록이 길게 이어진다.
400년 넘게 사람들이 가사를 바꿔 가며 불렀고, 19세기에는 성탄 찬송 「저 아기 잠들었네」가 되었다. 떠난 사람을 탓하지 않고 그리워하는 노래.""",
        "themes": ['이별', '짝사랑', '다 주었던 사랑', '그리움', '가을', '겨울'],
        "feel": "오래된 사랑 노래. 떠난 사람을 탓하지 않고 그리워하는 마음, 가을과 겨울 사이. 흔들리는 6/8 박자.",
        "sections": {
            "A": {
                "phrases": ["A4:1 C5:2 D5:1 E5:1.5 F5:0.5 E5:1 D5:2 B4:1 G4:1.5 A4:0.5 B4:1 C5:2 A4:1 A4:1.5 G#4:0.5 A4:1 B4:2 G#4:1 E4:2",
                            "A4:1 C5:2 D5:1 E5:1.5 F5:0.5 E5:1 D5:2 B4:1 G4:1.5 A4:0.5 B4:1 C5:1.5 B4:0.5 A4:1 G#4:1.5 F#4:0.5 G#4:1 A4:3 A4:2"],
                "chords": ["Am", "G", "Am", "E", "Am", "G", "Am E", "Am"],
            },
            "B": {
                "phrases": ["G5:3 G5:1.5 F#5:0.5 E5:1 D5:2 B4:1 G4:1.5 A4:0.5 B4:1 C5:2 A4:1 A4:1.5 G#4:0.5 A4:1 B4:2 G#4:1 E4:3",
                            "G5:3 G5:1.5 F#5:0.5 E5:1 D5:2 B4:1 G4:1.5 A4:0.5 B4:1 C5:1.5 B4:0.5 A4:1 G#4:1.5 F#4:0.5 G#4:1 A4:3 A4:3"],
                "chords": ["C", "G", "Am", "E", "C", "G", "Am E", "Am"],
            },
        },
        "map": {"verse": "A", "chorus": "B", "bridge": "A"},
        "arrangement": ["intro", "A", "B", "A", "B+", "outro"],
    },
    {
        "id": "moonlight", "name": "월광 소나타", "composer": "루트비히 판 베토벤", "year": "1801년",
        "key": "C#m", "time": 4, "bpm": 52, "pattern": "triplet",
        "story": """1801년 베토벤이 쓴 피아노 소나타 14번 「환상곡풍 소나타」. 제자였던 열일곱 살 줄리에타 귀차르디 백작 영애에게 헌정했다. 베토벤은 그녀를 사랑했으나 신분 차이로 결혼은 이뤄지지 않았다.
같은 해 베토벤은 친구 베겔러에게 처음으로 귀가 안 들린다는 사실을 편지로 고백했다. 1악장은 느린 셋잇단음표가 처음부터 끝까지 멈추지 않는다.
"월광"이라는 이름은 베토벤이 죽은 뒤 1832년 평론가 렐슈타프가 루체른 호수의 달빛 같다고 쓴 데서 왔다. 베토벤 자신은 그렇게 부른 적이 없다. 말하지 못한 것을 품고 잠들지 못하는 밤의 음악.""",
        "themes": ['잠 못 드는 밤', '비밀', '이룰 수 없는 사랑', '상실', '어둠', '달'],
        "feel": "멈추지 않는 셋잇단음 위에 같은 음을 두드리는 선율. 잠들지 못하는 밤, 말하지 못한 것, 창밖의 달. 아주 느리고 어둡다.",
        "sections": {
            "A": {
                "phrases": ["G#4:3 G#4:0.75 G#4:0.25 G#4:4",
                            "G#4:3 G#4:0.75 G#4:0.25 G#4:2 A4:2",
                            "A4:3 G#4:0.75 F#4:0.25 F#4:2 E4:2",
                            "E4:3 D#4:0.75 C#4:0.25 C#4:4"],
                "chords": ["C#m", "C#m", "C#m/B", "A", "A", "F#m", "G#7", "C#m"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "A"},
        "arrangement": ["intro", "A", "A+", "A", "outro"],
    },
    {
        "id": "gymnopedie", "name": "짐노페디 1번", "composer": "에릭 사티", "year": "1888년",
        "key": "D", "time": 3, "bpm": 66, "pattern": "waltz",
        "story": """1888년 스물두 살의 사티가 몽마르트르에서 쓴 곡. 당시 그는 카바레 '검은 고양이'에서 피아노를 치며 옷장만 한 방에서 살았다. 악보에는 "느리고 고통스럽게"라고 적혀 있다.
제목은 고대 스파르타 축제에서 벌거벗은 소년들이 추던 춤에서 왔지만, 음악은 춤이라기보다 멈춘 시간에 가깝다. 사티는 평생 혼자 살았고 죽은 뒤 방에서 한 번도 보내지 않은 편지들과 똑같은 회색 양복 여러 벌이 나왔다.
외로움을 울지 않고 견디는 사람의 음악. 비 오는 오후, 혼자 있는 방.""",
        "themes": ['혼자 사는 방', '외로움', '비 오는 날', '일요일', '멈춘 시간', '청춘'],
        "feel": "느린 왈츠, 비 오는 오후, 아무것도 하지 않는 시간. 쓸쓸한데 편안하다. 혼자 사는 방, 일요일 저녁.",
        "sections": {
            "A": {
                "phrases": ["F#5:1 A5:1 G5:1 F#5:1 C#5:1 B4:1 C#5:1 D5:1 A4:1 F#4:3 F#4:3",
                            "F#5:1 A5:1 G5:1 F#5:1 C#5:1 B4:1 C#5:1 D5:1 A4:1 F#4:3 F#4:3",
                            "A4:1 B4:1 C#5:1 D5:1 E5:1 C#5:1 D5:1 B4:1 A4:1 B4:3 A4:3"],
                "chords": ["Gmaj7", "Dmaj7", "Gmaj7", "Dmaj7", "Dmaj7", "Gmaj7", "Dmaj7", "Gmaj7", "Dmaj7", "Dmaj7", "Em", "A7", "Em", "A7", "D"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "A"},
        "arrangement": ["intro", "A", "A+", "A", "outro"],
    },
    {
        "id": "new_world", "name": "신세계 교향곡 라르고", "composer": "안토닌 드보르자크", "year": "1893년",
        "key": "C", "time": 4, "bpm": 58, "pattern": "block",
        "story": """1893년 드보르자크가 뉴욕 국립음악원 원장으로 있을 때 쓴 교향곡 9번 2악장. 그는 보헤미아의 고향을 몹시 그리워했고, 흑인 영가와 롱펠로의 시 「하이어워사」에서 받은 인상을 이 느린 악장에 담았다.
제자 해리 벌리가 불러 준 영가를 들으며 썼고, 여름에는 체코 이민자 마을인 아이오와 스필빌에 가서 가족과 함께 지냈다. 1922년 제자 윌리엄 암스 피셔가 이 선율에 「고잉 홈」이라는 가사를 붙여 집으로 돌아가는 노래가 되었다.
먼 곳에서 고향과 가족을 떠올리는 사람의 음악. 장례식과 졸업식, 하루의 끝에 불린다.""",
        "themes": ['고향', '집으로', '타향', '부모님', '하루의 끝', '떠나보냄', '졸업'],
        "feel": "집으로 돌아가는 노래. 먼 곳에서 떠올리는 고향, 부모님, 끝난 하루. 넓고 느리고 따뜻하다.",
        "sections": {
            "A": {
                "phrases": ["E4:1 G4:1 G4:2 E4:1 D4:1 C4:2 E4:1 G4:1 G4:2 E4:4",
                            "E4:1 G4:1 G4:2 E4:1 D4:1 C4:2 D4:1 E4:1 D4:1 C4:1 C4:4"],
                "chords": ["C", "C", "F", "C", "C", "Am", "F G", "C"],
            },
            "B": {
                "phrases": ["G4:1 E4:1 D4:1 C4:1 D4:1 E4:1 D4:1 C4:1 D4:4",
                            "G4:1 E4:1 D4:1 C4:1 D4:1 E4:1 G4:1 E4:1 D4:4"],
                "chords": ["Am", "F", "G", "G", "Am", "F", "G", "G"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "B"},
        "arrangement": ["intro", "A", "B", "A+", "outro"],
    },
    {
        "id": "amazing_grace", "name": "어메이징 그레이스", "composer": "존 뉴턴·전통 선율", "year": "1779년",
        "key": "G", "time": 3, "bpm": 72, "pattern": "waltz",
        "story": """가사는 1772년 영국의 존 뉴턴이 썼다. 그는 노예 무역선 선장이었다가 1748년 폭풍 속에서 배가 거의 가라앉을 때 처음 기도했고, 뒤에 목사가 되어 노예제 폐지 운동에 섰다.
"나 같은 죄인 살리신"으로 시작하는 가사는 자신이 한 일을 알고도 다시 살게 된 사람의 고백이다. 지금의 선율 「뉴 브리튼」은 1835년 미국에서 붙었다.
잃었다가 다시 찾은 사람, 한 번 더 기회를 얻은 사람의 노래. 장례식과 추모식에서 가장 많이 불린다.""",
        "themes": ['용서', '다시 시작', '후회', '떠난 사람', '추모', '두 번째 기회'],
        "feel": "잃었다가 다시 찾은 사람의 노래. 용서, 다시 시작하는 날, 떠난 사람을 보내는 자리. 넓고 느리다.",
        "sections": {
            "A": {
                "phrases": ["D4:1 G4:2 B4:0.5 G4:0.5 B4:2 A4:1 G4:2 E4:1 D4:2",
                            "D4:1 G4:2 B4:0.5 G4:0.5 B4:2 A4:1 D5:3 D5:2",
                            "B4:1 D5:2 B4:0.5 D5:0.5 B4:2 G4:1 D4:2 E4:0.5 G4:0.5 G4:2 E4:1 D4:2",
                            "D4:1 G4:2 B4:0.5 G4:0.5 B4:2 A4:1 G4:3 G4:2"],
                "chords": ["G", "G", "C", "G", "G", "G", "D", "D", "G", "G", "C", "G", "Em", "G", "D", "G"],
            },
        },
        "map": {"verse": "A", "chorus": "A", "bridge": "A"},
        "arrangement": ["intro", "A", "A+", "A", "outro"],
    },
    {
        "id": "bach_prelude", "name": "바흐 전주곡 C장조", "composer": "요한 제바스티안 바흐", "year": "1722년",
        "key": "C", "time": 4, "bpm": 68, "pattern": "none",
        "story": """1722년 바흐가 쓴 「평균율 클라비어곡집」 1권의 첫 곡. 표지에 "배우고자 하는 음악 청년들의 쓰임과 이익을 위해"라고 적었다. 아들 빌헬름 프리데만을 가르치려고 만든 연습장에서 나온 곡이다.
선율 없이 분산화음만 서른다섯 마디 이어진다. 1853년 구노가 이 위에 「아베 마리아」 선율을 얹었고, 그 뒤로 수많은 노래가 이 바탕 위에 쓰였다.
아버지가 아이를 위해 쓴 첫 페이지. 무엇이든 시작하는 자리의 음악.""",
        "themes": ['아버지', '처음', '배움', '아침', '시작', '아이'],
        "feel": "같은 분산화음이 물처럼 흐르는 곡. 선율이 아니라 바탕이라, 그 위에 어떤 노래든 얹을 수 있다. 아침, 창가, 처음 시작하는 날.",
        "sections": {
            "A": {
                "phrases": [" ".join(f"{n}:0.5" for n in ns) for ns in [
                    "C4 E4 G4 C5 E5 G4 C5 E5 C4 E4 G4 C5 E5 G4 C5 E5".split(),
                    "C4 D4 A4 D5 F5 A4 D5 F5 C4 D4 A4 D5 F5 A4 D5 F5".split(),
                    "B3 D4 G4 D5 F5 G4 D5 F5 B3 D4 G4 D5 F5 G4 D5 F5".split(),
                    "C4 E4 G4 C5 E5 G4 C5 E5 C4 E4 G4 C5 E5 G4 C5 E5".split(),
                    "C4 E4 A4 E5 A5 A4 E5 A5 C4 E4 A4 E5 A5 A4 E5 A5".split(),
                    "C4 D4 F#4 A4 D5 F#4 A4 D5 C4 D4 F#4 A4 D5 F#4 A4 D5".split(),
                    "B3 D4 G4 D5 G5 G4 D5 G5 B3 D4 G4 D5 G5 G4 D5 G5".split(),
                    "B3 C4 E4 G4 C5 E4 G4 C5 B3 C4 E4 G4 C5 E4 G4 C5".split(),
                ]],
                "chords": ["C", "Dm7/C", "G7/B", "C", "Am/C", "D7/C", "G/B", "Cmaj7/B"],
            },
        },
        "free_lyrics": True,
        "map": {"verse": "A", "chorus": "A", "bridge": "A"},
        "arrangement": ["A", "A", "A", "A", "outro"],
    },
]
BY_ID = {p["id"]: p for p in LIBRARY}


# ---------------------------------------------------------------- 음 이론

def midi(name: str) -> int:
    m = NOTE_RE.match(name)
    if not m:
        raise ValueError(f"음 이름이 이상합니다: {name}")
    pc = PC[m.group(1).upper()] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + pc


def freq(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def parse_chord(sym: str) -> tuple[int, list[int]]:
    """'F#m7/A' → (베이스 미디, 코드 구성음 미디 목록, 3~4옥타브)."""
    base, _, bass = sym.partition("/")
    m = re.match(r"^([A-G][#b]?)(.*)$", base)
    root = PC[m.group(1)[0]] + {"#": 1, "b": -1, "": 0}[m.group(1)[1:]]
    tones = QUALITY.get(m.group(2), QUALITY[""])
    notes = [48 + ((root + t) % 12) for t in tones]           # C3~B3 영역
    notes = [n + 12 if n < 52 else n for n in notes]           # E3 아래는 한 옥타브 올림
    bpc = PC[bass[0]] + {"#": 1, "b": -1, "": 0}[bass[1:]] if bass else root
    b = 36 + (bpc % 12)
    if b > 45:
        b -= 12
    return b, sorted(notes)


def parse_phrase(text: str) -> list[tuple[int | None, float]]:
    out = []
    for tok in text.split():
        name, _, beats = tok.partition(":")
        out.append((None if name == "r" else midi(name), float(beats)))
    return out


# ---------------------------------------------------------------- 신시사이저

def _piano(f: float, dur: float, vel: float) -> np.ndarray:
    tail = 1.2
    n = int((dur + tail) * SR)
    t = np.arange(n) / SR
    decay = 0.9 + f / 600.0
    env = (1 - np.exp(-t / 0.004)) * np.exp(-t * decay)
    gate = np.where(t > dur, np.exp(-(t - dur) * 9.0), 1.0)
    out = np.zeros(n)
    for k in range(1, 7):
        amp = vel * (0.55 ** (k - 1)) / (1 + (f * k / 4000) ** 2)
        fk = f * k * (1 + 0.0003 * k * k)
        if fk > SR / 2:
            break
        out += amp * np.sin(2 * math.pi * fk * t) * np.exp(-t * decay * (0.6 + 0.25 * k))
    return out * env * gate


def _reverb(x: np.ndarray, mix: float = 0.16) -> np.ndarray:
    rng = np.random.default_rng(3)
    L = int(1.4 * SR)
    ir = rng.normal(0, 1, L) * np.exp(-np.arange(L) / (0.45 * SR))
    ir[0] = 0
    ir /= np.sqrt((ir ** 2).sum())
    n = len(x) + L
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: len(x)]
    return x + mix * y


class Track:
    def __init__(self, seconds: float):
        self.buf = np.zeros(int(seconds * SR) + SR * 3)

    def note(self, m: int, start: float, dur: float, vel: float) -> None:
        s = _piano(freq(m), dur, vel)
        i = int(start * SR)
        j = min(len(self.buf), i + len(s))
        self.buf[i:j] += s[: j - i]


# ---------------------------------------------------------------- 편곡

def _bars(section: dict) -> list[str]:
    """마디별 코드 목록. 'F C7'처럼 한 마디에 둘이면 그대로 둔다(렌더에서 반씩)."""
    return list(section["chords"])


def _accomp(track: Track, piece: dict, chords: list[str], t0: float, spb: float, vel: float) -> None:
    time = piece["time"]
    pat = piece["pattern"]
    for i, sym in enumerate(chords):
        parts = sym.split()
        for pi, part in enumerate(parts):
            bar_t = t0 + i * time * spb + pi * (time / len(parts)) * spb
            span = time / len(parts)
            bass, notes = parse_chord(part)
            if pat == "none":
                continue
            if pat == "block":
                track.note(bass, bar_t, span * spb, vel * 0.9)
                for n in notes:
                    track.note(n, bar_t, span * spb, vel * 0.7)
            elif pat == "waltz":
                track.note(bass, bar_t, span * spb, vel * 0.9)
                for b in range(1, int(span)):
                    for n in notes:
                        track.note(n, bar_t + b * spb, spb * 0.9, vel * 0.6)
            elif pat == "arp8":
                seq = [bass, notes[-1], notes[0] + 12, notes[1], notes[-1], notes[0] + 12, notes[1], notes[-1]]
                for k in range(int(span * 2)):
                    track.note(seq[k % 8], bar_t + k * spb / 2, spb * 0.7, vel * (0.9 if k == 0 else 0.6))
            elif pat == "arp6":
                seq = [bass, notes[1], notes[-1], notes[0] + 12, notes[-1], notes[1]]
                for k in range(int(span)):
                    track.note(seq[k % 6], bar_t + k * spb, spb * 0.9, vel * (0.9 if k == 0 else 0.6))
            elif pat == "arp3":
                seq = [bass, notes[-1], notes[0] + 12]
                for k in range(int(span)):
                    track.note(seq[k % 3], bar_t + k * spb, spb * 0.9, vel * (0.9 if k == 0 else 0.55))
            elif pat == "triplet":
                track.note(bass, bar_t, span * spb, vel * 0.9)
                seq = [notes[0], notes[1], notes[-1]]
                for k in range(int(span * 3)):
                    track.note(seq[k % 3] + 12, bar_t + k * spb / 3, spb / 3 * 1.2, vel * 0.55)


def _melody(track: Track, phrases: list[str], t0: float, spb: float, vel: float, octave: int) -> float:
    t = t0
    for ph in phrases:
        for m, beats in parse_phrase(ph):
            if m is not None:
                track.note(m + 12 * octave, t, beats * spb * 0.95, vel)
            t += beats * spb
    return t


def section_beats(section: dict) -> float:
    return sum(b for ph in section["phrases"] for _, b in parse_phrase(ph))


def render_hand(piece_id: str, out_dir: Path) -> dict:
    """손으로 적은 선율로 멜로디+반주 MP3와 멜로디만 있는 MP3를 만든다."""
    piece = BY_ID[piece_id]
    spb = 60.0 / piece["bpm"]
    time = piece["time"]
    plan = []
    t = 0.0
    events: list[tuple[str, float, dict, int, bool]] = []  # (이름, 시작, 섹션, 옥타브, 멜로디 포함)
    for name in piece["arrangement"]:
        if name == "intro":
            sec = piece["sections"][piece["map"]["verse"]]
            bars = _bars(sec)[:4]
            events.append(("intro", t, {"chords": bars, "phrases": []}, 0, False))
            plan.append(("전주", t, len(bars) * time * spb))
            t += len(bars) * time * spb
        elif name == "outro":
            sec = piece["sections"][piece["map"]["chorus"]]
            bars = _bars(sec)[-2:]
            events.append(("outro", t, {"chords": bars, "phrases": []}, 0, False))
            plan.append(("후주", t, len(bars) * time * spb))
            t += len(bars) * time * spb
        else:
            key = name.rstrip("+")
            sec = piece["sections"][key]
            octave = 1 if name.endswith("+") and piece["pattern"] != "none" else 0
            events.append((key, t, sec, octave, True))
            dur = section_beats(sec) * spb
            plan.append((f"주제 {key}" + (" (옥타브 위)" if octave else ""), t, dur))
            t += dur
    total = t

    full, solo = Track(total), Track(total)
    for key, start, sec, octave, mel in events:
        _accomp(full, piece, sec["chords"], start, spb, 0.5)
        if mel:
            _melody(full, sec["phrases"], start, spb, 0.95, octave)
            _melody(solo, sec["phrases"], start, spb, 0.95, octave)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for label, tr in (("melody", full), ("melody-solo", solo)):
        x = _reverb(tr.buf)
        n = int(total * SR) + int(2.5 * SR)
        x = x[:n]
        fade = np.ones(len(x))
        fo = int(2.0 * SR)
        fade[-fo:] = np.linspace(1, 0, fo)
        x = x * fade
        x = x / max(1e-9, np.abs(x).max()) * 0.89
        wav = out_dir / f"{label}.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        mp3 = out_dir / f"{label}.mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
        wav.unlink()
        files[label] = mp3
    return {
        "id": piece_id, "name": piece["name"], "composer": piece["composer"],
        "seconds": round(total, 1), "bpm": piece["bpm"], "key": piece["key"],
        "plan": [{"part": p, "start": round(s, 1), "seconds": round(d, 1)} for p, s, d in plan],
        "source": "hand",
    }


# ---------------------------------------------------------------- 가사 계획

def syllables(section: dict) -> list[int]:
    """프레이즈마다 가사 음절을 얹을 수 있는 음 수(쉼표 제외)."""
    return [sum(1 for m, _ in parse_phrase(ph) if m is not None) for ph in section["phrases"]]


def lyric_plan_hand(piece_id: str) -> str:
    piece = BY_ID[piece_id]
    if piece.get("free_lyrics"):
        return (f"이 곡({piece['name']})은 분산화음 바탕이라 가사 줄 수와 음절 수는 자유다. "
                "4/4, 한 마디에 7~10음절 정도로 느긋하게 쓴다.")
    lines = [f"멜로디 곡: {piece['name']} ({piece['composer']}, {piece['key']}, {piece['bpm']} bpm). 가사는 이 멜로디에 그대로 얹어 부른다."]
    seen = {}
    for role in ("verse", "chorus", "bridge"):
        key = piece["map"][role]
        counts = syllables(piece["sections"][key])
        seen[role] = (key, counts)
    role_ko = {"verse": "[Verse 1], [Verse 2]", "chorus": "[Chorus], [Final Chorus]", "bridge": "[Bridge]"}
    for role, (key, counts) in seen.items():
        lines.append(f"- {role_ko[role]}: 주제 {key}, 줄 {len(counts)}개, 줄마다 음절 수 {' / '.join(map(str, counts))} (±1까지 허용)")
    lines.append("- 긴 음이 있는 자리에는 '아', '어', '오'처럼 열린 모음(아, 어, 오)을 둔다. 음 수보다 음절이 적으면 한 음절을 두 음에 걸쳐 불러도 되지만 가능하면 맞춘다.")
    lines.append("- 쉼표(r) 자리는 숨 쉬는 곳이라 음절을 넣지 않는다. [Pre-Chorus]와 [Intro], [Outro]는 쓰지 않는다.")
    return "\n".join(lines)


# ---------------------------------------------------------------- 카탈로그

def is_public_domain(p: dict) -> bool:
    died, year = p.get("died"), p.get("year")
    return isinstance(died, int) and isinstance(year, int) and died <= PD_DIED_BEFORE and year <= PD_YEAR_BEFORE


def catalog(available_only: bool = True) -> list[dict]:
    """catalog.yaml의 곡 목록. 저작권 규칙을 통과하고(기본) 선율 데이터가 있는 곡만."""
    data = yaml.safe_load((ASSETS / "catalog.yaml").read_text(encoding="utf-8")) or {}
    out = []
    for p in data.get("pieces", []):
        if not is_public_domain(p):
            continue
        p = dict(p)
        p["midi"] = (MIDI_DIR / f"{p['id']}.mid") if (MIDI_DIR / f"{p['id']}.mid").exists() else None
        p["available"] = bool(p["midi"]) or p.get("hand") in BY_ID
        if available_only and not p["available"]:
            continue
        out.append(p)
    return out


def get(piece_id: str) -> dict:
    for p in catalog(available_only=False):
        if p["id"] == piece_id:
            return p
    raise KeyError(piece_id)


def lyric_plan(piece_id: str) -> str:
    p = get(piece_id)
    if p["midi"]:
        from . import midi
        return midi.lyric_plan(p["midi"], p["name"])
    return lyric_plan_hand(p["hand"])


def render(piece_id: str, out_dir: Path) -> dict:
    p = get(piece_id)
    if p["midi"]:
        from . import midi
        info = midi.render(p["midi"], out_dir)
    else:
        info = render_hand(p["hand"], out_dir)
    info.update({"id": p["id"], "name": p["name"], "composer": p["composer"]})
    return info


def catalogue() -> str:
    """선택용 자료: 지금 쓸 수 있는 곡마다 배경 이야기와 주제어, 가사 계획."""
    out = []
    for p in catalog():
        out.append(f"### {p['id']} — {p['name']} ({p['composer']}, {p['year']}년)")
        out.append(p["story"].strip())
        out.append("어울리는 주제어: " + ", ".join(p.get("themes", [])))
        out.append(lyric_plan(p["id"]))
        out.append("")
    return "\n".join(out)
