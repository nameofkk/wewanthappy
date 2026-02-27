# WeWantHappy 프로젝트 규칙

## 자동 Git Push
**이 프로젝트에서 파일을 수정할 때마다 작업 완료 후 반드시 자동으로 실행:**
```bash
cd /home/krshin7/Projects/wewanthappy
git add .
git commit -m "작업 내용 한 줄 요약"
git push
```
- remote: `https://github.com/nameofkk/wewanthappy`
- branch: `main`
- 인증: remote URL에 토큰 포함되어 있음 (별도 설정 불필요)
- 커밋 메시지: 한국어 OK, 작업 내용 한 줄 요약

## 배포 정보 (미설정 — Railway 새 프로젝트 필요)
- Domain: `https://www.wewanthappy.live` (DNS 미연결)
- Railway: 새 프로젝트 생성 필요 (WeWantPeace와 완전 별개)
- DB: 별도 Supabase/Railway PostgreSQL 인스턴스 필요

## railway.json 주의사항
- `railway.json`은 **backend** 서비스용으로 유지 (`Dockerfile.backend`)
- worker 배포 시: 임시로 `Dockerfile.worker`로 변경 후 배포, 즉시 복원
- frontend 배포 시: 임시로 `Dockerfile.frontend`로 변경 후 배포, 즉시 복원

## i18n 규칙
- UI 텍스트 수정 시 한국어(ko) + 영어(en) 동시 수정
- `frontend/lib/i18n.ts` — ko/en 블록 모두 업데이트

## normalizer.py 수정 시
- 수정 후 반드시 `python3 scripts/reprocess_topics.py` 실행
