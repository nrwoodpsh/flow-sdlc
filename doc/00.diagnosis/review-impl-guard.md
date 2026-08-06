# 구현 반증 — 가드·게이트 (커밋 15cdd60)

돌아가는 코드를 실제 명령으로 공격한 결과. 기준선 재확인: `hooks.test.sh` 283 통과·0 실패 · `lint.test.py` 검사 13 전부 통과 · `gen_docs --check` 4곳 일치 · `bump --check` 일치. **이 통과 상태에서 아래가 뚫린다.**

## Critical

### C1. 게이트 면제 우회 — `..` 로 면제 접두어를 달고 실제로는 소스에 쓴다
게이트는 경로 문자열의 **접두어**로 면제를 판정하는데 내부 `..` 를 정규화하지 않는다. 그래서 `doc/`·`spike/` 로 시작하면 면제되지만 셸·Write 도구는 `..` 를 풀어 진짜 소스 파일에 쓴다. **Write 훅 경로와 Bash 경로 양쪽에서 재현.**
```
# 미선언 src/secret.ts 에 쓰는데 게이트는 allow:
printf '{"tool_input":{"file_path":"doc/../src/secret.ts"}}'   | gate-source-write.sh   → rc=0 (allow: not-source "doc/ 아래")
printf '{"tool_input":{"file_path":"spike/../src/secret.ts"}}' | gate-source-write.sh   → rc=0 (allow: spike 면제)
echo x > doc/../src/secret.ts    (guard→gate)                                            → rc=0 PASS   (디스크: src/secret.ts)
echo x > spike/../src/secret.ts  (guard→gate)                                            → rc=0 PASS   (디스크: src/secret.ts)
# 대조 — 정직한 경로는 정상 차단:
printf '{"tool_input":{"file_path":"src/secret.ts"}}' | gate-source-write.sh             → rc=2 DENY
```
게이트의 **존재 이유(미선언 소스 쓰기 차단)가 문자 3개(`../`)로 완전히 무력화된다.** `os.path.normpath` 로 접두어·글로브 판정 전에 경로를 정규화하고, 정규화 후 `..` 가 남으면 거부해야 한다. (`.claude/../`·`.github/..` 는 우연히 막히는데, 그건 방어가 아니라 `rel.lstrip('./')` 가 앞 `.` 을 먹어 접두어가 안 맞아서다 — M2 참조.)

## High

### H1. 인용 삽입으로 명령 낱말을 쪼개 가드를 통과 — 되돌릴 수 없는 명령까지
스캐너가 인용 **내용**을 공백으로 바꾸는데(커밋 메시지의 `"git push"` 를 데이터로 보려는 의도), 낱말 매칭이 그 결과를 쓴다. 그래서 명령 낱말 안에 인용을 한 글자라도 끼우면 낱말이 갈라져 규칙이 안 맞는다. 셸은 그대로 실행한다.
```
git p"u"sh origin main          → rc=0 PASS   (실행: git push)
git res"e"t --hard HEAD         → rc=0 PASS   (실행: git reset --hard — 되돌릴 수 없음)
git commit --no-veri"f"y        → rc=0 PASS   (실행: 방어층 끄기)
gh secret "set" X               → rc=0 PASS   (실행: gh secret set)
gh "pr" merge 1                 → rc=0 PASS   (실행: gh pr merge)
git pu""sh origin main          → rc=2 BLOCK  (빈 인용 `""` 은 공백을 안 넣어 안 갈라짐)
```
v1 원본도 동일하게 뚫린다(읽기만 확인 — v1 clean). 즉 **이식된 스캐너에서 상속된 구멍**이다. 그런데 v2 가드는 스스로 *"세그먼트 안 어느 자리의 git·gh 도 명령으로 본다"* 며 안전 측을 자처하고, `limits` 에 이 형태를 **적지 않았다**(적힌 한계는 eval·변수 쪼갬·스크립트 파일·MCP·사람 편집기뿐). 최소한 `guard-rules.json` 의 `limits` 에 명시해야 하고, `reset --hard`·`push` 가 한 글자로 뚫리는 만큼 Critical 로 볼 여지가 있다.

### H2. Bash 쓰기 탐지 목록이 불완전 — 파일 생성 명령 다수와 `>|` 가 게이트에 안 물어봄
`WRITE_CMDS` 는 `tee`·`sed -i`·`perl -i`·`gsed` 넷뿐이고 리다이렉션은 `>` 만 본다. 파일을 **만드는** 다른 명령과 noclobber 리다이렉션이 새어, 게이트가 아예 호출되지 않는다.
```
cp a.ts src/secret.ts           → rc=0 PASS      mv /tmp/x src/secret.ts   → rc=0 PASS
dd of=src/secret.ts if=…        → rc=0 PASS      truncate -s0 src/secret.ts→ rc=0 PASS
ln -sf /tmp/x src/secret.ts     → rc=0 PASS      echo x >| src/secret.ts   → rc=0 PASS  (`>|` 는 `|` 가 경계라 대상 표시가 지워짐)
# 대조 — 잡히는 것: cat>· echo>· >>· printf>· tee· sed -i· heredoc>· |tee· 1> 는 전부 rc=2 BLOCK
```
`python3 -c "open(...,'w')"` 통과는 `limits` 에 적혀 있어 정직한 한계(OK)지만, 위 `cp`·`mv`·`dd`·`truncate`·`ln`·`>|` 는 **한계로도 안 적혀 있다.** 목록에 추가하거나 한계로 명시해야 한다.

## Medium

### M1. 가드는 정본 부재 시 fail-open, 게이트는 fail-to-ask — 비대칭
`guard-rules.json` 이 없거나 깨지면 가드는 stderr 경고 후 **rc=0 통과**(되돌릴 수 없는 명령까지 안 막음). 주석에 근거가 있다(막으면 사람이 훅을 지운다). 게이트는 topology 부재·손상 시 **rc=3 ask** 로 사람에게 넘긴다(근거 주석 있음).
```
git push  (FLOW_GUARD_RULES=/nonexistent)  → rc=0 PASS "아무것도 막지 않는 상태입니다"
git push  (깨진 JSON)                       → rc=0 PASS  동일
```
둘 다 문서화된 선택이지만, **되돌릴 수 없는 명령을 막는 층이 조용히(경고 한 줄) 꺼진다**는 점이 더 위험한 쪽이다. 바쁜 세션에서 stderr 경고는 놓치기 쉽다. 최소한 rules 부재를 `check-drift-hook.sh` 처럼 SessionStart 에서 한 번 크게 알리는 것을 검토.

### M2. `rel.lstrip('./')` 는 접두어가 아니라 문자 집합을 벗긴다
`gate-source-write.sh` 의 python 판정부는 `rel = rel.replace(os.sep,'/').lstrip('./')` 로 정규화하는데, `lstrip('./')` 는 앞쪽 `.` 와 `/` 를 **전부** 벗긴다. `.claude/x` → `claude/x`, `...a` → `a`. C1 에서 `.claude/../` 가 우연히 안 뚫린 것이 이 부작용이고, 반대로 정상 dotfile 경로 판정을 틀리게 할 수 있다. `추측`: 실제 오분류 사례는 이 세션에서 못 만들었으나, 정규화 로직 자체가 틀렸다.

## 안 뚫린 것 (시도했고 방어가 유효)
- **가드 우회 시도 전부 정상 차단**: `-XPOST`↔`-X POST`↔`--method=POST`, `-c core.hooksPath=` 위치 이동(`git -c … commit` / `git commit -c …`), `--no-verify`·단축 `-n`, `commit --amend && push`(연쇄 끝의 block 을 봄), `sh -c`·`bash -c`·`timeout bash -c` payload, `command git push`, `GIT_DIR= git push`, heredoc 안 `git push`.
- **과차단 회귀 없음**: `branch -d`(소문자)·`stash list`·`config --get`·`gh pr view`·`gh api -X GET`·`push --dry-run`·`merge --abort`·`restore --staged`·정상 `commit -m` 전부 통과.
- **생성물 대조**: 표 한 행 삭제·공백만 변경·생성 블록 통째 제거 → `gen_docs --check`·`lint.py generated-up-to-date` 가 셋 다 rc=1 로 잡음.
- **CI**: `ci.yml` 이 5개 검사(lint.test→lint→gen --check→bump --check→hooks.test)를 다 돌리고 `continue-on-error` 없음. 도구(node·perl 등) 부재를 통과로 세지 않게 선검사. `lint.test` 를 `lint` **앞**에 둠(사문화 방어).
- **배선**: `Write|Edit|MultiEdit|NotebookEdit` → 게이트 연결 확인, 미선언 소스 rc=2. MCP 파일 도구는 hooks.json·limits 에 한계로 명시됨.
- **변수 쪼갬·별칭**(`p=push; git $p`, `git ci --amend`): 통과하나 `limits` 에 적힌 정직한 한계.

## 원복 확인
v2 실험은 `scratchpad/` 와 `CLAUDE.md`(변조 후 복원, `git diff` 없음)에만 했다. `git status`: `doc/02.skills-map.md`·`plugins/flow/skills/` 가 untracked 로 보이나 **내 작업이 아니다**(mtime 09:02~09:05, 설계자의 미커밋 스킬 분할 작업 — 나는 그 경로에 쓴 적 없음). v1(`/Users/soulers/WKSPCES/flow-sdlc`)은 `git status` clean 확인.
