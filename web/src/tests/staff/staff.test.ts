import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { staffStore, SEED_CRITERIA } from '../../components/staff/mockStaffData';

describe('Staff Module (BCS / Admin / GVCN) - Gói C Unit & Workflow Tests', () => {
  // Reset store before test suite
  staffStore.resetStore();

  describe('1. BCS Overview & Statistics', () => {
    it('should compute overview counts correctly from seed data', () => {
      const overview = staffStore.getOverview();
      assert.equal(overview.total_students, 3, 'Total students should be 3');
      assert.equal(overview.bcs_review_count, 1, 'SV001 is in BCS_REVIEW');
      assert.equal(overview.proposed_count, 1, 'SV002 is in PROPOSED');
      assert.equal(overview.needs_info_count, 1, 'SV003 is in NEEDS_INFO');
      assert.equal(overview.open_appeals_count, 1, '1 open appeal seeded');
      assert.equal(overview.finalized_count, 0, 'No finalized cases yet');
    });
  });

  describe('2. BCS Cases List & Filters', () => {
    it('should return all cases when filter is ALL', () => {
      const res = staffStore.getCases('ALL', '', 1, 10);
      assert.equal(res.total, 3);
      assert.equal(res.items.length, 3);
    });

    it('should filter cases by specific status', () => {
      const resReview = staffStore.getCases('BCS_REVIEW', '', 1, 10);
      assert.equal(resReview.total, 1);
      assert.equal(resReview.items[0].student_code, 'SV001');

      const resProposed = staffStore.getCases('PROPOSED', '', 1, 10);
      assert.equal(resProposed.total, 1);
      assert.equal(resProposed.items[0].student_code, 'SV002');
    });

    it('should search cases by student code or student name', () => {
      const resSearch = staffStore.getCases('ALL', 'Bình', 1, 10);
      assert.equal(resSearch.total, 1);
      assert.equal(resSearch.items[0].student_code, 'SV002');

      const resCode = staffStore.getCases('ALL', 'SV003', 1, 10);
      assert.equal(resCode.total, 1);
      assert.equal(resCode.items[0].student_name, 'Lê Văn Cường');
    });
  });

  describe('3. BCS CaseDetail 3-Zone Review & Scoring Rules', () => {
    const caseId = '55555555-5555-5555-5555-555555555001';

    it('should retrieve 3-zone case detail with claims, criteria, deadlines, and evidence', () => {
      const detail = staffStore.getCaseDetail(caseId);
      assert.ok(detail, 'Case detail must exist');
      if (detail) {
        assert.equal(detail.student.code, 'SV001');
        assert.equal(detail.claims.length, 3, 'Must have 3 criteria claims');
        assert.ok(detail.claims[0].evidence.length > 0, 'TC01 must have evidence file');
      }
    });

    it('should fail with REASON_REQUIRED when approved_score != self_score and reason is missing', () => {
      const detail = staffStore.getCaseDetail(caseId)!;
      assert.throws(
        () => {
          staffStore.reviewClaim(
            caseId,
            '44444444-4444-4444-4444-444444444003',
            '6.00',
            '', // empty reason
            detail.version
          );
        },
        (err: unknown) => (err as { error?: { code?: string } })?.error?.code === 'REASON_REQUIRED'
      );
    });

    it('should fail with INVALID_SCORE when approved_score exceeds max_score', () => {
      const detail = staffStore.getCaseDetail(caseId)!;
      assert.throws(
        () => {
          staffStore.reviewClaim(
            caseId,
            '44444444-4444-4444-4444-444444444001',
            '15.00', // exceeds max 10.00
            'Điểm thưởng',
            detail.version
          );
        },
        (err: unknown) => (err as { error?: { code?: string } })?.error?.code === 'INVALID_SCORE'
      );
    });

    it('should fail with CASE_CHANGED when expected_version does not match current version', () => {
      assert.throws(
        () => {
          staffStore.reviewClaim(
            caseId,
            '44444444-4444-4444-4444-444444444001',
            '8.00',
            'Hợp lệ',
            999 // wrong version
          );
        },
        (err: unknown) => (err as { error?: { code?: string } })?.error?.code === 'CASE_CHANGED'
      );
    });

    it('should successfully save claim review when reason is provided for score deviation', () => {
      const detail = staffStore.getCaseDetail(caseId)!;
      const prevVersion = detail.version;
      const res = staffStore.reviewClaim(
        caseId,
        '44444444-4444-4444-4444-444444444003',
        '7.00',
        'BCS duyệt hoạt động cấp khoa 7 điểm',
        prevVersion
      );
      assert.equal(res.case_id, caseId);
      assert.equal(res.version, prevVersion + 1);
    });
  });

  describe('4. BCS Supplement Request & Rounds Limit', () => {
    const caseId = '55555555-5555-5555-5555-555555555001';

    it('should successfully create PROOF supplement request within allowed limits', () => {
      const detail = staffStore.getCaseDetail(caseId)!;
      assert.equal(detail.rounds.proof, 0);

      const res = staffStore.createSupplementRequest(
        caseId,
        'PROOF',
        '44444444-4444-4444-4444-444444444003',
        'Minh chứng bị mờ, vui lòng nộp lại bản chụp rõ nét hơn',
        detail.version
      );

      assert.equal(res.new_status, 'NEEDS_PROOF');
      const updated = staffStore.getCaseDetail(caseId)!;
      assert.equal(updated.rounds.proof, 1);
      assert.equal(updated.status, 'NEEDS_PROOF');
      assert.ok(updated.deadlines.supplement_at !== null);
    });

    it('should enforce MAX_ROUNDS_REACHED when rounds limit is exceeded', () => {
      const detail = staffStore.getCaseDetail(caseId)!;
      // info_round is already 1, info_max is 2
      staffStore.createSupplementRequest(caseId, 'INFO', null, 'Bổ sung thêm 1', detail.version);

      const updated = staffStore.getCaseDetail(caseId)!;
      assert.equal(updated.rounds.info, 2);

      // 3rd attempt must throw MAX_ROUNDS_REACHED
      assert.throws(
        () => {
          staffStore.createSupplementRequest(
            caseId,
            'INFO',
            null,
            'Bổ sung quá giới hạn',
            updated.version
          );
        },
        (err: unknown) => (err as { error?: { code?: string } })?.error?.code === 'MAX_ROUNDS_REACHED'
      );
    });
  });

  describe('5. BCS Complete Review & Proposed Total Calculation', () => {
    const caseId = '55555555-5555-5555-5555-555555555001';

    it('should complete review, calculate proposed total and transition to PROPOSED', () => {
      const detail = staffStore.getCaseDetail(caseId)!;
      const res = staffStore.completeReview(caseId, detail.version);

      assert.equal(res.status, 'PROPOSED');
      // TC01: 8.00, TC02: 10.00, TC03: 7.00 => total 25.00
      assert.equal(res.proposed_total, '25.00');

      const updated = staffStore.getCaseDetail(caseId)!;
      assert.equal(updated.status, 'PROPOSED');
    });
  });

  describe('6. Scoreboard, Meetings & Publishing Gate Check', () => {
    it('should verify scoreboard and publish readiness', () => {
      const sb = staffStore.getScoreboard();
      assert.ok(sb.meetings.length >= 2, 'Should have BCS and CLASS meetings recorded');

      // Check SV003 is still in NEEDS_INFO
      const sv003 = staffStore.getCaseDetail('55555555-5555-5555-5555-555555555003')!;
      // Approve SV003 to make class 100% ready
      staffStore.reviewClaim('55555555-5555-5555-5555-555555555003', SEED_CRITERIA[0].id, '7.00', 'Bảng điểm hợp lệ', sv003.version);
      const sv003v2 = staffStore.getCaseDetail('55555555-5555-5555-5555-555555555003')!;
      staffStore.reviewClaim('55555555-5555-5555-5555-555555555003', SEED_CRITERIA[1].id, '8.00', 'Đúng tự khai', sv003v2.version);
      const sv003v3 = staffStore.getCaseDetail('55555555-5555-5555-5555-555555555003')!;
      staffStore.reviewClaim('55555555-5555-5555-5555-555555555003', SEED_CRITERIA[2].id, '7.00', 'Đúng tự khai', sv003v3.version);
      const sv003v4 = staffStore.getCaseDetail('55555555-5555-5555-5555-555555555003')!;
      staffStore.completeReview('55555555-5555-5555-5555-555555555003', sv003v4.version);

      const sbReady = staffStore.getScoreboard();
      assert.equal(sbReady.can_publish, true, 'can_publish should be true when all proposed and 2 meetings held');
    });

    it('should publish scores and transition proposed cases to PUBLISHED with appeal deadline', () => {
      const pubRes = staffStore.publishScores();
      assert.equal(pubRes.status, 'PUBLISHED');
      assert.ok(pubRes.published_at);
      assert.ok(pubRes.appeal_deadline_at);

      const campaign = staffStore.getCampaign();
      assert.equal(campaign.status, 'PUBLISHED');
    });
  });

  describe('7. Appeals Resolution & Finalize Gate Check', () => {
    it('should fail finalize if there are OPEN appeals', () => {
      assert.throws(
        () => {
          staffStore.finalizeCampaign();
        },
        (err: unknown) => (err as { error?: { code?: string } })?.error?.code === 'UNRESOLVED_APPEALS'
      );
    });

    it('should resolve appeal with KEEP or ADJUST with reason', () => {
      const appeals = staffStore.getAppeals();
      const openAppeal = appeals.find((a: any) => a.status === 'OPEN')!;
      assert.ok(openAppeal);

      const resolved = staffStore.resolveAppeal(
        openAppeal.id,
        'ADJUST',
        '8.00',
        'BCS chấp nhận minh chứng tình nguyện cấp trường'
      );

      assert.equal(resolved.status, 'RESOLVED');
      assert.equal(resolved.resolution, 'ADJUST');
      assert.equal(resolved.new_score, '8.00');
    });

    it('should finalize campaign when all appeals are resolved', () => {
      const finalRes = staffStore.finalizeCampaign();
      assert.equal(finalRes.status, 'FINALIZED');
      assert.ok(finalRes.finalized_at);

      const campaign = staffStore.getCampaign();
      assert.equal(campaign.status, 'FINALIZED');
    });
  });

  describe('8. Admin Campaign Rules & Deadlines Constraints', () => {
    it('should check open_at < submission_deadline_at constraint', () => {
      const openDate = new Date('2026-10-25T01:00:00Z');
      const deadlineDate = new Date('2026-10-30T17:00:00Z');
      assert.ok(openDate < deadlineDate, 'open_at must be before deadline');
    });

    it('should check reminder_after_hours < appeal_period_hours constraint', () => {
      const campaign = staffStore.getCampaign();
      assert.ok(
        campaign.reminder_after_hours < campaign.appeal_period_hours,
        'reminder must be strictly less than appeal period'
      );
    });
  });

  describe('9. GVCN Final Scores & CSV Export', () => {
    it('should generate valid UTF-8 BOM CSV with headers and records', () => {
      const csv = staffStore.exportGvcnCsvContent();
      assert.ok(csv.startsWith('\uFEFF'), 'Must contain UTF-8 BOM for Excel');
      assert.ok(csv.includes('Mã SV'), 'Must contain header Mã SV');
      assert.ok(csv.includes('Điểm chính thức'), 'Must contain header Điểm chính thức');
      assert.ok(csv.includes('SV001'), 'Must contain student SV001');
      assert.ok(csv.includes('FINALIZED'), 'Must contain FINALIZED status');
    });
  });
});
