# 레퍼런스 조사

## 레퍼런스 조사에 대한 메모
이번에는 웹 검색을 새로 돌리지 않았습니다. 붙어 있는 감성 레퍼런스 프로필(터치드, 크라잉넛, 극동아시아타이거즈)과 이전 곡 목록을 기준으로 썼습니다. 차트와 명곡 사례는 확인하지 않았습니다.

가져온 원리는 다음과 같습니다.
- 터치드: 후렴의 영어 낱말 하나를 반복해 훅으로 쓴다.
- 극동아시아타이거즈: 제목이 후렴에 들어가고, 마지막 후렴에서 한 단어만 바꾼다.
- 크라잉넛: 거창한 말 옆에 초라한 생활 사물을 붙인다.

## 후렴 후보 5개
1. **hero 내 영웅 / 보자기 망토 hero / hero 내 영웅 / 올려다봤던 hero**
2. hero 불러 본다 / 현관 앞에서 / hero 불러 본다 / 큰 소리로
3. 날 줄 알았지 hero / 날 줄 알았지 hero
4. 쓰러져도 hero / 일어나는 hero
5. 내 키가 커도 hero

**선택은 1번입니다.**
- 훅 "hero 내 영웅"은 5음절이고 소리 내어 외치기 쉽습니다. 설명 없이 뜻이 통하고, 듣는 사람이 자기가 동경하던 사람을 대입할 수 있습니다.
- 2번은 장면이 약하고, 3번과 5번은 재치가 먼저 보입니다.
- 4번은 뜻이 교훈에 가깝습니다. 그래서 4번의 내용은 브릿지로 옮겼습니다.

## Suno 스타일 문구
```
Korean rock, classic riff-driven hard rock with 2000s band energy, swaggering mid-tempo around 122 bpm, bright major key with a short minor turn in the pre-chorus. Male tenor-baritone vocal, gritty but warm, slightly raspy, plain and sincere, chest voice, sung in Korean, korean lyrics. Sparse lyrics, lots of instrumental space. Intro: one bluesy pentatonic guitar riff alone, then drums and bass lock in. Verse: palm-muted riff, dry punchy drums, round picked bass, short talky lines. Pre-chorus: second guitar, rising repeated note, snare roll. Chorus: two distorted guitars left and right, crash cymbals, upward leap on the word "hero", gang shout on the hook only, long held last note. Verse 2 adds a lead guitar answering the vocal. 8-bar melodic guitar solo after chorus two. Bridge drops to half-time, bass and one clean guitar, near-spoken voice. Final chorus biggest, octave-up harmony, hard stop, last word sung alone. Live room, analog warmth.
```

## 가사 (제목: hero)

[Intro]
(기타 리프)

[Verse 1]
보자기를 목에 묶고
옥상 난간 위로
뛰었지 날 줄 알고
무릎에 생긴 흉터

[Pre-Chorus]
밥상을 물리고
리모컨을 쥐고
그 사람이 나올 때까지

[Chorus]
hero 내 영웅
보자기 망토 hero
hero 내 영웅
올려다봤던 hero

[Verse 2]
키는 이제 내가 크네
월급날엔 치킨도 사네
이름은 가물가물
등짝만 선명해

[Pre-Chorus]
리모컨을 쥐고
밥상을 물리고
그 사람이 나올 때까지

[Chorus]
hero 내 영웅
보자기 망토 hero
hero 내 영웅
올려다봤던 hero

[Guitar Solo]

[Bridge]
이기던 장면만 기억했네
넘어지던 건 지웠네
너 따라 뛰던 꼬마야
그 사람 진짜였대
보고 싶다

[Final Chorus]
hero 내 영웅
보자기 망토 hero
hero 내 영웅
닮고 싶던 hero

## 설계 점검
- **훅**: "hero"는 후렴 12줄에 들어가고, 제목이 곧 후렴입니다. 마지막 후렴은 "올려다봤던"이 "닮고 싶던"으로 한 줄만 바뀝니다. 브릿지에는 훅이 없습니다.
- **화법**: 직전 두 곡(우리, 너에게)을 피해 혼잣말과 관찰로 갔습니다. 브릿지에서 "너"가 한 번 나옵니다. 어릴 적 자신을 부르는 말입니다.
- **브릿지**: 영웅이 이기는 사람이 아니라 넘어져도 일어나는 사람이었다는, 곡에서 처음 나오는 인정이 들어 있습니다. 감정어는 "보고 싶다"를 한 번만 직접 썼습니다.
- **유머**: 치킨 한 줄만 두었습니다.
- **줄 끝**: 명사 끊김(흉터, 등짝만 선명해), 반말 -네, -지, 연결형이 섞여 있습니다. 한 구간이 같은 어미로만 끝나지 않습니다.
- **버릇말과 이전 곡**: 목록의 버릇말과 이전 곡 후렴의 소재는 쓰지 않았습니다.
- **길이**: "가사 내용 많이 넣지 말기" 요청대로 본문은 줄였습니다. 대신 인트로 리프와 솔로 8마디로 곡 길이를 채워 3분 안팎이 되게 했습니다.
