# 태깅

**직접 충족하는 ID만** 태그한다. 부모는 **전이로 추적**된다 — 재기입하면 부모가 바뀔 때 두 곳을 고쳐야 해 드리프트가 난다.

```
SYS-1 → USER-1 → USER-LOGIN-1 → D-1 → 2.task/00.login-api → 4.build/… → 5.verify/…
                       ↑ 상단 1회 선언        ↑ frontmatter
```

- **예외**: 횡단 요구(`SYS-*`)는 기능 요구의 부모 체인에 없으므로 **설계 요소가 직접 태그**한다.

## 어디에 무엇을 적나

| 파일 | 무엇 |
|:--|:--|
| `1.design.md` | 설계 요소 표에 `\| D-N \| 요소 \| 충족 요구 \|` |
| `2.task/NN.name.md` | frontmatter 의 `requirement:` · `design:` |
| `4.build`·`5.verify` | task 번호·이름과 함께 **태그도 상속**한다 |

```yaml
---
requirement: [USER-LOGIN-1]
design: [D-1]
---
```

- **`requirement:` frontmatter 가 기계 게이트의 판정 근거다** — 소스를 쓰려면 이 태그가 있어야 한다(`flow.topology.json` 의 `gate` 절).
- **본문에서 ID 모양을 grep 해 태그로 세지 않는다** — `UTF-8`·`ISO-8601` 이 요구 ID 모양과 같아 오탐이 난다.
- **채워지지 않은 템플릿(`{{USER-LOGIN-1}}`)은 태그가 없는 것이다.** 그게 실제 상태다.
