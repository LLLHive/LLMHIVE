import { redirect } from "next/navigation"

/** Common typo of /landing/ad1-free (letter l vs digit 1). */
export default function AdlFreeTypoRedirect() {
  redirect("/landing/ad1-free")
}
