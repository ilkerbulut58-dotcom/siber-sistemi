import { Navbar } from "@/components/navbar";
import { RedirectIfAuthed } from "@/components/redirect-if-authed";
import { HomeContent } from "@/components/home-content";

export default function HomePage() {
  return (
    <>
      <RedirectIfAuthed />
      <Navbar />
      <HomeContent />
    </>
  );
}
