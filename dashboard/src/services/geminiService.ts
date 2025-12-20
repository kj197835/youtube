import { VideoData, ChannelStats, AIInsight } from "../types";

export const getCreatorInsights = async (
    stats: ChannelStats,
    recentVideos: VideoData[]
): Promise<AIInsight[]> => {
    // Simulating API delay
    await new Promise(resolve => setTimeout(resolve, 800));

    // Simple Rule-based Logic to replace Gemini for now
    const engagement = stats.avgEngagementRate;
    let engagementInsight: AIInsight;

    if (engagement > 10) {
        engagementInsight = {
            topic: "High Engagement",
            analysis: "Your audience is extremely active compared to channel average.",
            recommendation: "Ask more questions in comments to sustain this momentum.",
            impact: "High"
        };
    } else {
        engagementInsight = {
            topic: "Retention Focus",
            analysis: "Engagement is steady but could be higher.",
            recommendation: "Try adding a pinned comment with a question.",
            impact: "Medium"
        };
    }

    const growthInsight: AIInsight = {
        topic: "Subscriber Growth",
        analysis: `You gained ${stats.subscriberCount > 0 ? 'subscribers' : 'steady traction'} this period.`,
        recommendation: "Consider making a 'Thank You' community post.",
        impact: "Medium"
    };

    const contentInsight: AIInsight = {
        topic: "Content Strategy",
        analysis: "Your recent video views indicate a stable core audience.",
        recommendation: "Analyze your top clicked video's thumbnail style.",
        impact: "High"
    };

    return [engagementInsight, growthInsight, contentInsight];
};
