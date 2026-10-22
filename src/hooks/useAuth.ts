import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";

/** Current signed-in student (null when signed out, undefined while checking). */
export function useAuthUser() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    void supabase.auth.getUser().then(({ data }) => alive && setUser(data.user ?? null));
    const { data } = supabase.auth.onAuthStateChange((_e, session) => setUser(session?.user ?? null));
    return () => {
      alive = false;
      data.subscription.unsubscribe();
    };
  }, []);
  return user;
}
