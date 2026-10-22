import { queryOptions } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

export interface TopicProgress { topic: string; score: number; correct_count: number; wrong_count: number }

export const progressQuery = queryOptions({
  queryKey: ["topic-progress"],
  queryFn: async (): Promise<TopicProgress[]> => {
    const { data, error } = await supabase.from("topic_progress").select("topic, score, correct_count, wrong_count");
    if (error) throw new Error("Couldn't load your progress.");
    return data ?? [];
  },
});

/** Saves one answer; the database applies +10 / -5 and keeps the score between 0 and 100. */
export async function recordAnswer(topic: string, correct: boolean): Promise<TopicProgress> {
  const { data, error } = await supabase.rpc("record_answer", { _topic: topic, _correct: correct });
  if (error || !data) throw new Error("Couldn't save your answer.");
  return data as TopicProgress;
}
