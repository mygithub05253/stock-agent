# `docs/presentation/` - 발표 자료

> 프로젝트 시연과 중간·최종 발표에 사용하는 브라우저 기반 자료를 보관합니다.

## 현재 파일

`midterm_presentation.html`은 중간 발표 시점의 시스템·성과·로드맵을 담은 HTML deck입니다.

`final_presentation_source.json`은 2026-06-27 최종 발표 19장 구성의 원천 데이터입니다. 시장 문제 정의, 팀원 역할, Agent 필요성, 시스템 흐름, Agent별 상세 설명, 시연 영상 큐, 상업성, 한계와 결론을 한 파일에서 관리합니다.

`final_presentation.html`은 최종 발표용 브라우저 슬라이드입니다. PDF 변환의 기준 파일이며 키보드 좌우 방향키로 넘길 수 있습니다.

`final_presentation.pdf`는 프로젝터 발표 백업용 16:9 PDF입니다. 발표장 뷰어 호환성을 높이기 위해 렌더링 이미지를 다시 묶은 평탄화 PDF로 생성합니다.

`final_presentation.pptx`는 PowerPoint 편집용 산출물입니다. 텍스트, 표, 도형은 대부분 편집 가능한 PPTX 요소로 구성했고, 실제 화면과 아키텍처 이미지만 이미지 자산으로 포함했습니다.

`final_presentation_script.html`은 19장 슬라이드별 발표 대본입니다. 핵심 메시지, 발표 멘트, 전환 문장을 함께 담았습니다.

`final_presentation_qa.html`은 5분 Q&A 대비 문서입니다. 예상 질문별 짧은 답변, 보충 설명, 피해야 할 표현을 정리했습니다.

`build_final_presentation_html.mjs`는 `final_presentation_source.json`을 바탕으로 HTML 슬라이드를 재생성하는 스크립트입니다.

`build_final_presentation_pptx.mjs`는 `final_presentation_source.json`을 바탕으로 PPTX를 재생성하는 스크립트입니다. 기본 실행은 PPTX만 생성합니다.

`build_final_presentation_pdf.py`는 HTML 렌더링 결과를 Chrome으로 PDF화한 뒤, 각 페이지를 이미지로 다시 묶어 호환성 높은 PDF를 생성하는 스크립트입니다.

```powershell
$env:HOME='C:\Users\kik32'
$node='C:\Users\kik32\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$python='C:\Users\kik32\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $node docs\presentation\build_final_presentation_html.mjs
& $node docs\presentation\build_final_presentation_pptx.mjs
& $python docs\presentation\build_final_presentation_pdf.py
```

## 관리 원칙

- 발표 자료의 수치에는 평가 리포트나 구현 문서 링크를 둡니다.
- 당시 상태를 보존하되 현재 구현처럼 오해되지 않도록 날짜를 표시합니다.
- 발표 전 브라우저 해상도와 로컬 asset 로딩을 확인합니다.
- 비밀값과 개인 데이터는 포함하지 않습니다.

[상위 문서 인덱스](../README.md)
