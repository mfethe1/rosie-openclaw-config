export interface OutlookConfig {
  draftMode: boolean;
  autoSend: boolean;
}

export interface ProcoreSyncStatus {
  lastSync: Date;
  status: 'PENDING' | 'SYNCED' | 'FAILED';
  errorMessage?: string;
}

export interface SimpleEstimateFlow {
  estimateId: string;
  totalAmount: number;
  isSmallShop: boolean;
  simplifiedWorkflowEnabled: boolean;
}

export class ProcoreIntegrationService {
  public async syncWithProcore(estimateId: string): Promise<ProcoreSyncStatus> {
    return {
      lastSync: new Date(),
      status: 'SYNCED',
    };
  }

  public async draftOutlookInvite(
    recipient: string,
    template: string,
    config: OutlookConfig
  ): Promise<boolean> {
    if (config.draftMode && !config.autoSend) {
      console.log(`Drafting email to ${recipient} with template ${template}`);
      return true;
    }
    console.log(`Sending email to ${recipient} with template ${template}`);
    return true;
  }

  public createSimplifiedEstimate(amount: number): SimpleEstimateFlow {
    return {
      estimateId: Math.random().toString(36).substring(7),
      totalAmount: amount,
      isSmallShop: true,
      simplifiedWorkflowEnabled: true,
    };
  }
}
