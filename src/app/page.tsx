import {cookies} from 'next/headers';
import ScamShieldDashboard from '@/components/scamshield-dashboard';

export default async function Page() {
  const preferences = await cookies();
  return <ScamShieldDashboard
    initialOnboarding={preferences.get('scamguard-onboarded')?.value !== '1'}
    initialLanguage={preferences.get('scamguard-language')?.value === 'vi' ? 'vi' : 'en'}
    initialTheme={preferences.get('scamguard-theme')?.value === 'light' ? 'light' : 'muted'}
  />;
}
