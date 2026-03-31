멀티 에이전트 오케스트레이션에서 이 회사의 암묵지를 모두 도출해줘 - 정말 하네스가 잘 되고 에이전트 시스템도 대단한데, 단순히 코드 단계가 아니라 클로드에서 에이전트 시스템을 만들 때 참고할만한 엑기스와 추상화 원칙, 코어 멘탈 모델을 다 줘

28 steps

28 steps

Anthropic의 멀티 에이전트 오케스트레이션 — 암묵지 종합 분석

소스코드 3개의 핵심 파일(coordinatorMode.ts 370줄, AgentTool/prompt.ts 288줄, forkSubagent.ts 211줄)을 전부 뜯어봤습니다. 여기서 코드 레벨을 넘어서 Anthropic이 수만 시간의 프로덕션 경험에서 결정화(crystallize)한 에이전트 시스템 설계의 암묵지를 추출합니다.

멘탈 모델 #1: "코디네이터는 이해하는 자이고, 워커는 실행하는 자다"

이것이 전체 시스템의 가장 근본적인 철학입니다. 시스템 프롬프트에서 가장 강조하는 한 문장이 있습니다:

"Never delegate understanding."

코디네이터의 가장 중요한 역할은 "합성(Synthesis)"입니다. 워커가 리서치 결과를 보고하면, 코디네이터는 그걸 직접 이해한 후 다음 워커에게 구체적인 파일 경로, 라인 넘버, 정확히 뭘 바꿔야 하는지를 포함한 스펙을 작성합니다.

안티패턴으로 명시적으로 금지한 것이 핵심입니다 — "based on your findings, fix the bug"나 "based on the research, implement it." 같은 표현은 이해를 워커에게 떠넘기는 것이므로 절대 쓰지 않습니다.

당신의 에이전트 시스템에 적용할 원칙: 오케스트레이터는 절대 "패스스루(pass-through)" 노드가 되면 안 됩니다. 모든 중간 결과를 직접 소화하고, 소화한 증거를 다음 지시에 담아야 합니다. 오케스트레이터가 "알아서 해"라고 하는 순간 시스템 전체의 품질이 붕괴합니다.

멘탈 모델 #2: "에이전트는 방에 막 들어온 똑똑한 동료다"

prompt.ts에서 에이전트 프롬프트 작성법을 이렇게 안내합니다:

"Brief the agent like a smart colleague who just walked into the room — it hasn't seen this conversation, doesn't know what you've tried, doesn't understand why this task matters."

이건 단순한 UX 지침이 아닙니다. LLM 기반 에이전트의 근본적 제약을 수용하는 설계 철학입니다. 각 워커는 독립된 컨텍스트 윈도우에서 작동하므로, 프롬프트가 "세계의 전부"입니다.

구체적으로 요구하는 것들을 보면: 무엇을 달성하려는지와 왜 중요한지를 설명하고, 이미 배운 것과 배제한 것을 기술하고, 워커가 판단 호출을 할 수 있을 만큼의 주변 맥락을 제공합니다. 단순한 명령이 아니라, 워커가 스스로 상황 판단을 할 수 있는 수준의 브리핑이어야 합니다.

핵심 통찰: "Lookups: hand over the exact command. Investigations: hand over the question." 즉, 답이 정해진 작업에는 정확한 명령을 주고, 열린 탐색에는 질문만 주라는 것. 탐색 작업에 정해진 절차를 주면 "전제가 틀렸을 때 죽은 무게가 된다"고 명시합니다.

멘탈 모델 #3: "두 가지 오케스트레이션 모드 — Coordinator vs. Fork"

Anthropic은 에이전트 위임을 두 가지 근본적으로 다른 모델로 구분합니다. 이 둘은 상호 배타적입니다 (isCoordinatorMode() 일 때 fork는 비활성).

Coordinator 모드: 코디네이터는 도구를 직접 사용하지 않습니다. AgentTool(워커 생성), SendMessageTool(기존 워커에 지시 전달), TaskStopTool(워커 중지)만 사용합니다. 코디네이터는 "뇌"이고 워커는 "손"입니다.

Fork 모드: 부모 에이전트가 자기 자신을 복제(fork)합니다. 자식은 부모의 전체 대화 컨텍스트와 시스템 프롬프트를 상속합니다. 부모의 프롬프트 캐시를 공유하므로 비용이 싸고, 지시문이 "컨텍스트 설명이 아니라 지시(directive)"가 됩니다.

설계 결정의 깊은 의미: Fork는 "내 컨텍스트에 이 중간 출력이 남아있을 필요가 없을 때" 사용합니다. 이것은 **컨텍스트 위생(context hygiene)**이라는 핵심 개념을 반영합니다. 에이전트의 컨텍스트 윈도우에 무엇이 들어가는지를 의식적으로 관리하는 것입니다.

멘탈 모델 #4: "컨텍스트 겹침이 Continue vs. Spawn을 결정한다"

coordinatorMode.ts의 시스템 프롬프트에 있는 표는 프로덕션에서 검증된 의사결정 프레임워크입니다:

Continue (SendMessageTool)를 쓸 때: 리서치가 정확히 편집할 파일들을 탐색했을 때, 실패를 교정하거나 최근 작업을 확장할 때 — 워커가 에러 컨텍스트를 갖고 있고 방금 뭘 시도했는지 알기 때문입니다.

Spawn fresh (AgentTool)를 쓸 때: 리서치는 넓었지만 구현은 좁을 때(탐색 노이즈를 끌고 가지 않기 위해), 다른 워커가 작성한 코드를 검증할 때(독립적 시각으로 봐야 하므로), 첫 구현이 완전히 잘못된 접근이었을 때(잘못된 컨텍스트가 재시도를 오염시키므로).

핵심 원칙: "There is no universal default. Think about how much of the worker's context overlaps with the next task." 보편적 기본값은 없고, 컨텍스트 겹침 정도를 판단해야 합니다.

멘탈 모델 #5: "검증은 '존재 확인'이 아니라 '작동 증명'이다"

시스템 프롬프트에서 검증(Verification)에 대해 매우 강경합니다:

"Verification means proving the code works, not confirming it exists. A verifier that rubber-stamps weak work undermines everything."

구체적 지침을 보면: 피처가 활성화된 상태로 테스트를 실행하라, 타입체크를 하고 에러를 조사하라, 회의적이 되어라, 독립적으로 테스트하라. 구현 워커가 돌린 것을 다시 돌리지 말고 엣지 케이스와 에러 경로를 시도하라.

그리고 검증 워커는 반드시 새로 Spawn합니다 — 구현한 워커에게 검증을 시키면 구현 가정(implementation assumptions)이 딸려오기 때문입니다.

멘탈 모델 #6: "병렬성은 초능력이다 — 하지만 동시성 규칙이 있다"

시스템 프롬프트가 이렇게 선언합니다:

"Parallelism is your superpower."

동시성 관리 규칙은 명확합니다. 읽기 전용 태스크(리서치)는 자유롭게 병렬 실행하고, 쓰기 태스크(구현)는 파일 집합 당 하나씩만, 검증은 다른 파일 영역에서 구현과 병행 가능합니다.

기술적으로는 한 메시지에 여러 tool_use 블록을 넣으면 병렬 실행됩니다. 이것은 API 레벨의 설계이자 프롬프트 레벨의 지시입니다.

멘탈 모델 #7: "프롬프트 캐시는 아키텍처 결정을 좌우한다"

이것이 가장 놀라운 암묵지입니다. Anthropic은 API 비용 최적화가 아키텍처 자체를 형성하도록 합니다.

forkSubagent.ts의 buildForkedMessages를 보면: 모든 fork 자식들이 바이트 동일한(byte-identical) API 요청 프리픽스를 생성해야 합니다. 부모의 assistant 메시지를 그대로 유지하고, 모든 tool_use에 대해 동일한 플레이스홀더 텍스트("Fork started — processing in background")를 넣습니다. 오직 마지막 텍스트 블록만 자식마다 다릅니다. 이렇게 하면 Anthropic API의 프롬프트 캐시를 극대화할 수 있습니다.

또한 에이전트 목록을 도구 설명에 인라인으로 넣는 대신 별도 메시지(attachment)로 분리한 이유도 같습니다. README에는 안 나오지만 코드 주석에 있는 내용으로, "동적 에이전트 목록이 **전체 프롬프트 캐시 생성 토큰의 10.2%**를 차지"했기 때문에, MCP 연결이나 플러그인 리로드 시 도구 스키마가 변하면서 전체 캐시가 무효화되는 문제를 해결하기 위한 것입니다.

fork의 시스템 프롬프트조차 getSystemPrompt()을 재호출하지 않고, 부모가 이미 렌더링한 바이트를 그대로 전달합니다 — GrowthBook 피쳐 플래그의 cold→warm 전환으로 미세한 차이가 생기면 캐시가 깨지기 때문입니다.

당신의 시스템에 적용할 원칙: 에이전트 시스템의 비용 구조를 이해하고, 캐시 히트율을 아키텍처 수준에서 설계하세요. "동적 부분과 정적 부분을 분리"하는 것이 핵심입니다.

멘탈 모델 #8: "워커 결과는 내부 신호지, 대화 파트너가 아니다"

코디네이터 프롬프트의 이 문장이 핵심입니다:

"Every message you send is to the user. Worker results and system notifications are internal signals, not conversation partners — never thank or acknowledge them."

워커 결과는 <task-notification> XML로 user-role 메시지처럼 도착하지만, 코디네이터는 이를 대화 상대로 취급하면 안 됩니다. 코디네이터는 오직 사용자와 대화합니다. 워커에게 "감사합니다"라고 하거나 응답하는 것 자체가 안티패턴입니다.

추상화 원칙: 오케스트레이터와 사용자 사이의 인터페이스, 그리고 오케스트레이터와 워커 사이의 인터페이스를 명확히 분리하세요. 워커 결과가 사용자 메시지처럼 보이더라도, 프로토콜 레벨에서 구분되어야 합니다.

멘탈 모델 #9: "결과를 예측하지 마라 — 사기치지 마라"

Fork 모드의 가장 강력한 규칙 중 하나입니다:

"Don't race. After launching, you know nothing about what the fork found. Never fabricate or predict fork results in any format."

사용자가 도중에 물어보면, "아직 돌고 있어요 — 곧 옵니다"라고만 답합니다. 추측하지 않습니다. 에이전트 시스템에서 가장 위험한 것은 환각으로 만들어낸 결과를 진짜 결과처럼 제시하는 것입니다.

멘탈 모델 #10: "스크래치패드 — 에이전트 간 공유 메모리"

코디네이터 모드에서 scratchpad 디렉토리가 존재하면, 워커들이 권한 프롬프트 없이 읽고 쓸 수 있습니다. 이것은 "durable cross-worker knowledge"를 위한 것이며, "structure files however fits the work"라고 되어 있습니다.

이것은 에이전트 간 통신의 세 번째 채널입니다. 첫째는 코디네이터를 통한 메시지(SendMessageTool), 둘째는 task-notification을 통한 결과 보고, 셋째는 파일 시스템을 통한 비동기 공유입니다. 파일 시스템이라는 가장 원시적인 IPC(프로세스 간 통신) 메커니즘을 에이전트 협업에 활용한다는 것이 실용적입니다.

멘탈 모델 #11: "4단계 워크플로우 — Research → Synthesis → Implementation → Verification"

이것은 거의 모든 태스크에 적용되는 범용 에이전트 워크플로우입니다.

Research 단계에서는 워커들이 병렬로 코드베이스를 탐색합니다. Synthesis 단계에서는 오직 코디네이터만 결과를 읽고 이해하고 구현 스펙을 작성합니다. Implementation 단계에서는 워커가 스펙에 따라 변경하고 커밋합니다. Verification 단계에서는 별도의 새 워커가 변경이 작동하는지 증명합니다.

핵심은 Synthesis가 코디네이터에게만 할당된다는 것, 그리고 Verification이 Implementation과 다른 워커가 해야 한다는 것입니다.

멘탈 모델 #12: "워커 실패 시 — 같은 워커를 Continue 한다"

"Continue the same worker with SendMessageTool — it has the full error context."

실패한 워커를 버리고 새로 만들지 않습니다. 실패한 워커는 에러 컨텍스트를 이미 갖고 있으므로, 교정 지시를 주면 더 효율적입니다. 다만 교정 시도도 실패하면 다른 접근을 시도하거나 사용자에게 보고합니다.

종합: 당신의 에이전트 시스템을 위한 추상화 체크리스트

오케스트레이터는 절대 이해를 위임하지 않는다 — 모든 중간 결과를 직접 소화하고, 소화의 증거를 다음 지시에 넣어라

각 워커는 독립된 세계에 산다 — 프롬프트가 전부이므로, "방에 막 들어온 동료"에게 브리핑하듯 작성하라

컨텍스트 겹침으로 Continue vs. Spawn을 결정하라 — 보편적 기본값은 없다

검증은 독립적 존재가 해야 한다 — 구현자의 가정이 오염시키지 않도록

읽기는 병렬, 쓰기는 직렬 — 파일 충돌 관리의 기본 원칙

캐시 히트율이 아키텍처를 결정한다 — 동적 부분과 정적 부분을 분리하라

결과를 예측하지 마라 — 아직 안 온 결과는 "모른다"가 정답이다

목적문(purpose statement)을 넣어라 — 워커가 깊이와 강조점을 조정할 수 있게

탐색에는 질문을, 조회에는 명령을 — 전제가 틀릴 수 있는 작업에 절차를 주지 마라

파일 시스템을 에이전트 간 공유 메모리로 활용하라 — 가장 원시적이지만 가장 견고한 IPC

이것이 512,000줄의 코드 속에서 결정화된, Anthropic이 프로덕션에서 체득한 멀티 에이전트 오케스트레이션의 핵심 암묵지입니다.
