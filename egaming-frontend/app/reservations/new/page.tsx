import { Suspense } from 'react';
import NewReservationClient from './NewReservationClient';

export default function NewReservationPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <NewReservationClient />
    </Suspense>
  );
}