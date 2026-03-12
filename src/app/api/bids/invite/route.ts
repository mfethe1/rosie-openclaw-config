import { NextResponse } from 'next/server';
import { ProcoreIntegrationService } from '@/lib/procore-integration';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { recipient, template, isSmallShop, amount, autoSend } = body;

    const procoreService = new ProcoreIntegrationService();

    let estimateDetails = null;
    if (isSmallShop && amount) {
      estimateDetails = procoreService.createSimplifiedEstimate(amount);
    }

    const emailSent = await procoreService.draftOutlookInvite(
      recipient,
      template,
      { draftMode: true, autoSend: !!autoSend }
    );

    let syncStatus = null;
    if (estimateDetails) {
      syncStatus = await procoreService.syncWithProcore(estimateDetails.estimateId);
    }

    return NextResponse.json({
      success: true,
      emailSent,
      estimateDetails,
      syncStatus,
    });
  } catch (error) {
    console.error('Failed to process invite:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to process invite' },
      { status: 500 }
    );
  }
}
