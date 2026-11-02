"""Privileged local operator workflow. Never exposed through the public API.

The operator must independently verify registration or guardian authority.
Evidence references identify secure operator-held evidence, not uploaded IDs.
"""
import argparse
import asyncio
from pathlib import Path
import uuid
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.local", override=True)
import bootstrap_imports  # noqa: E402,F401
from services.health_service.care.models import Clinician, Patient, VerificationDecision
from services.health_service.db.session import _SessionLocal, _engine


async def verify(args):
    async with _SessionLocal() as db:
        model = Clinician if args.kind == "clinician" else Patient
        row = await db.get(model, args.id, with_for_update=True)
        if row is None or (args.kind == "guardian" and row.relationship != "child"):
            raise SystemExit("Matching verification subject not found")
        if args.kind == "clinician":
            row.verified = args.decision == "approve"
        else:
            row.guardian_verified = args.decision == "approve"
        db.add(VerificationDecision(subject_id=args.id,subject_kind=args.kind,operator=args.operator,
            evidence_reference=args.evidence_reference,approved=args.decision=="approve"))
        await db.commit()
    await _engine.dispose()
    print("Verification decision recorded. No patient data was printed.")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind",choices=["clinician","guardian"])
    parser.add_argument("id",type=uuid.UUID)
    parser.add_argument("decision",choices=["approve","revoke"])
    parser.add_argument("--operator",required=True)
    parser.add_argument("--evidence-reference",required=True)
    arguments=parser.parse_args()
    if not 1<=len(arguments.operator)<=120 or not 1<=len(arguments.evidence_reference)<=200:
        parser.error("Operator and evidence reference must be nonempty and within 120/200 characters")
    asyncio.run(verify(arguments))
