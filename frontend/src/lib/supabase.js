import { createClient } from "@supabase/supabase-js"


const supabaseUrl = import.meta.env.VITE_SUPABASE_URL 
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY 

const configured = !!(supabaseUrl && supabaseKey)

if (!configured) {
  console.warn(
    "[Supabase] VITE_SUPABASE_URL or VITE_SUPABASE_KEY not set. " +
    "Realtime features will not work. Fill in frontend/.env and restart Vite."
  )
}

// Only create a real client if both values are present.
// Falls back to a no-op stub so the rest of the app loads normally.
export const supabase = configured
  ? createClient(supabaseUrl, supabaseKey)
  : {
      channel: () => ({
        on: function () { return this },
        subscribe: function () { return this },
      }),
      removeChannel: () => {},
    }
