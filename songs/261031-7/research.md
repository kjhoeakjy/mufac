# 레퍼런스 조사

레퍼런스 조사부터 하겠습니다.
Returns a JSON string. Parse it.
## 조사 결과

웹 검색은 첫 호출에서 형식 오류가 났고, 다시 시도하자 도구 사용 한도에 걸렸습니다. 그래서 다음은 확인하지 못했습니다.
- 시티팝 명곡 6~10곡의 연도와 후렴 분석
- 최근 멜론·유튜브 뮤직 차트와 쇼츠 곡, AI 곡
- 감성 레퍼런스 추가 검색

곡별 분석은 근거 없이 쓰면 지어낸 것이 되므로 싣지 않았습니다. 아래 원칙은 제가 알고 있는 시티팝 일반 문법과 첨부된 프로필·점검표에서 가져왔습니다.

레퍼런스 팀은 정서가 가까운 두 팀을 골랐습니다.
- **한로로**: 고장 난 사물을 먼저 놓고 감정을 말하는 방식을 가져옵니다.
- **극동아시아타이거즈**: 사소한 사물에서 그리움을 꺼내고, 2절은 1절의 틀에 낱말만 바꾸는 방식을 가져옵니다.

## 후렴 후보 5개

| # | 후보 | 음절 | 판단 |
|---|---|---|---|
| 1 | 빈 화분이야 | 5 | 이미지는 선명하지만 설명 문장에 가깝습니다. |
| 2 | 물 줄게 천천히 | 6 | 다정하지만 '천천히'가 군더더기입니다. |
| 3 | **비워둘게** | 4 | 열린 모음으로 끝나 늘여 부를 수 있습니다. 설명 없이 뜻이 통하고, 듣는 사람이 자기 일로 받을 수 있습니다. |
| 4 | 흙은 아직 따뜻해 | 7 | 장면은 좋지만 외치기 어렵습니다. |
| 5 | 거기 둬도 돼 | 5 | 입말이지만 주제가 흐립니다. |

**선택: 3번 「비워둘게」.** 누구에게나 비워 둔 자리가 있습니다. 그 자리가 사람일 수도 있고 시간이나 마음일 수도 있어서 추상적인 요청에 맞습니다. 화분은 그 자리를 담는 그릇으로만 씁니다. 후렴은 낮은 햇빛 한 장면으로 받칩니다.

## Suno 스타일 문구

```
Korean city pop, 80s rainy-window AOR groove, around 98 bpm, hazy and weightless, major seventh chords with a bittersweet minor turn in the pre-chorus. Female soprano-leaning vocal, airy and floating, soft head voice with a little breath, relaxed just behind the beat, close and dry verses, abstract and gentle, sung in Korean, korean lyrics. Warm synth bass with rounded sine-like tone and a soft kick lead the groove, brushed-sounding drum machine with gated snare and quiet hi-hats. Vibraphone and Rhodes chords carry verse 1, lots of space, narrow talky melody. Pre-chorus: clean chorus-effect guitar enters on a rising repeated note as a Juno pad swells. Chorus: upward leap on the first word, short hook with a long held last note, wide airy pads, soft stacked backing harmonies on the hook. Verse 2 adds a marimba figure answering the vocal. Short flute-like synth solo after chorus two. Bridge drops to Rhodes and near-whispered voice, bass stops. Final chorus fullest and widest, extra harmonies, held last note, outro fades on vibraphone alone. Gated reverb, wide stereo, analog warmth. Dreamy, quiet, sunlit.
```

이전 시티팝 세 곡과의 차이는 다음과 같습니다.
- 템포를 98 bpm으로 낮췄습니다.
- 보컬을 소프라노 쪽 공기감으로 잡았습니다.
- 슬랩 베이스 대신 신스 베이스를 씁니다.
- 비브라폰과 마림바를 넣었습니다.
- 브라스를 쓰지 않습니다.

## 가사

**제목: 비워둘게**

```
[Verse 1]
창가에 흙 한 줌
아직 이름이 없어
빛이 먼저 다녀가고
나는 컵에 물을 받네
초록이 될지 모를 것
모르는 채로 두는 일
너는 어디쯤이니
바람이 대신 묻고 가

[Pre-Chorus]
조금만 더
조금만 더 기울면
쏟아질 것 같은데

[Chorus]
비워둘게 네 자리
화분 옆 낮은 햇빛
오면 거기 앉아
비워둘게

[Verse 2]
선반에 잎 한 장
어제보다 기울었네
달이 늦게 들렀다가
내 컵만 비우고 가
잎이 나보다 느긋해
보고 싶다 말은 접어 둬
너는 아직 멀어
바람은 또 대신 묻고 가

[Pre-Chorus]
조금만 더
조금만 더 기울면
쏟아질 것 같은데

[Chorus]
비워둘게 네 자리
화분 옆 낮은 햇빛
오면 거기 앉아
비워둘게

[Bridge]
사실은 말이야
비어 있던 건 나였어
채울 줄 몰랐을 뿐
흙은 벌써 숨 쉬는데

[Final Chorus]
비워둘게 네 자리
화분 옆 낮은 햇빛
안 와도 내가 앉아
비워둘게
비워둘게
```

### 설계 점검
- **훅**: 「비워둘게」가 모두 7번 나옵니다. 후렴마다 첫 줄과 끝 줄에 있고, 마지막 후렴에서만 한 번 더 반복합니다. 제목이 후렴 안에 있습니다.
- **후렴**: 후렴은 네 줄입니다. 첫 후렴은 1절 8줄 바로 뒤에 나옵니다. 브릿지에는 훅이 없습니다.
- **기승전결**: 1절과 2절은 같은 틀에 낱말만 바꿨습니다(흙 한 줌 → 잎 한 장, 해 → 달). 2절 끝에서 "보고 싶다"를 직접 말합니다. 브릿지에서 처음으로 "비어 있던 건 나"라고 인정합니다. 마지막 후렴은 "오면 거기 앉아"가 "안 와도 내가 앉아"로 바뀝니다. 기다리는 쪽이 스스로 자리를 채웁니다.
- **말투**: 줄 끝은 명사·관형형 끊김, 연결어미, 반말, 혼잣말 -니, -네가 섞입니다. -다 종결은 없습니다. 줄은 대부분 5~9음절입니다. 웃음은 "잎이 나보다 느긋해" 한 줄만 둡니다.
- **이전 곡과의 겹침**: 후렴 소재와 말투는 이전 곡들과 겹치지 않습니다. 이번 곡만 빈자리, 햇빛, 기다림의 부드러운 반말 독백입니다.
- **미확인 부분**: 줄 길이와 훅 횟수는 직접 셌습니다. 차트 곡은 확인하지 못해서 최근 유행 곡과의 겹침 여부는 점검하지 못했습니다.

## 이번 곡에 가져갈 원칙
1. 추상은 사물 하나(화분, 컵, 햇빛)에 붙들어 매고, 설명은 하지 않습니다.
2. 훅은 4음절 안팎의 열린 모음으로 합니다. 시티팝의 느린 호흡에서 늘여 부르기 좋습니다.
3. 시티팝 보컬은 줄 사이를 비워 둡니다. 줄을 짧게 끊고 연결어미를 섞어 숨 쉴 자리를 만듭니다.
4. 1절과 2절은 틀을 유지하고 명사만 바꿉니다.
5. 감정어는 한 번만 직접 말합니다("보고 싶다").
6. 브릿지는 처음 하는 말, 즉 인정으로 둡니다.
7. 마지막 후렴은 한 줄만 바꿔 화자의 태도를 뒤집습니다.
8. 편곡은 후렴에서 가장 넓히고 브릿지에서 베이스를 뺍니다.

## 분포
- **제목 형태**: 이번 곡 제목은 반말 약속형 동사 하나입니다. 이전 후렴들은 명령, 의문, 명사구, 구호가 섞여 있었고, 이번에는 부드러운 약속형이라 겹치지 않습니다.
- **줄 끝**: 명사·관형형 끊김이 약 40%, 연결어미가 약 20%, 해체 종결이 약 30%, 혼잣말 -니와 -네가 약 10%입니다.
