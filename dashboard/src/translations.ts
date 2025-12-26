export const translations = {
    en: {
        // Build & Meta
        title: "AI Sound Lab",
        subtitle: "Manage your channel performance and strategy.",
        lastUpdated: "Last updated:",
        loading: "Loading Dashboard Data...",
        sectionComingSoon: "Section coming soon...",

        // Navigation
        nav: {
            dashboard: "Dashboard",
            content: "Contents",
            analytics: "Prediction",
            earn: "Earn",
            customization: "Customization"
        },

        // Subtitles for each section
        subtitles: {
            dashboard: "Manage your channel performance and strategy.",
            contents: "Manage and optimize your video library and metadata.",
            analytics: "Forecast your channel's growth for the next 30 days with AI predictions."
        },

        // Time Ranges
        timeRange: {
            daily: "Last 30 Days",
            weekly: "Last 30 Weeks",
            monthly: "Last 30 Months"
        },

        // Stats Cards
        stats: {
            subscribers: "Subscribers",
            views: "Total Views",
            revenue: "Revenue",
            watchTime: "Watch Time (Hrs)",
            engagement: "Engagement Rate"
        },

        // ... existing keys ...

        // Dashboard Section
        sections: {
            growth: "Growth",
            performance: "Performance",
            aiInsights: "AI Strategic Insights",
            aiForecast: "Future Growth Strategy", // New key
            aiSubtitle: "Strategic insights derived from growth predictions.",
            aiRec: "RECOMMENDATION",
            detailedAnalytics: "30-Day Growth Forecast", // Renamed
            predictionDisclaimer: "This is a prediction for the next 30 days based on current trends.", // New key
            topVideos: "Contents",
            noData: "No detailed trend data available for this period.",
            noDataSub: "Daily stats might be hidden by YouTube for privacy."
        },

        // Dropdowns
        metrics: {
            views: "Views",
            watchTime: "Watch Time",
            subscribers: "Subscribers",
            revenue: "Revenue",
            likes: "Likes",
            dislikes: "Dislikes",
            engagement: "Engagement"
        },
        predictionModels: {
            ma: "Simple Moving Average",
            wma: "Weighted Moving Average (Default)",
            xgboost: "XGBoost (AI)"
        },
        chartType: {
            changes: "Changes",
            cumulative: "Cumulative"
        },
        videoLimit: {
            all: "ALL"
        },

        // Table Headers
        table: {
            image: "Image",
            video: "Video",
            id: "ID",
            views: "Views",
            likes: "Likes",
            dislikes: "Dislikes",
            revenue: "Revenue"
        },

        // Footer & Legal
        footer: {
            copyright: "© 2025 AI Sound Lab. All rights reserved.",
            privacy: "Privacy Policy",
            tos: "Terms of Service",
            close: "Close"
        },

        // Legal Content Titles
        legal: {
            privacyTitle: "Privacy Policy",
            tosTitle: "Terms of Service",
            lastUpdated: "Last updated: December 21, 2025",
            effectiveDate: "Effective Date: December 21, 2025",

            // Privacy Content (Simplified for variable insertion)
            privacyIntro: 'At AI Sound Lab ("we," "our," or "us"), we value your privacy. This Privacy Policy explains how we collect, use, and protect your information when you use our YouTube Analytics Dashboard (the "Service").',
            privacySection1: "1. Information We Collect",
            privacyList1: [
                "YouTube Data: We access public and private channel data (views, subscribers, revenue, etc.) via the YouTube Data API and Analytics API.",
                "Usage Data: We may collect anonymous usage statistics to improve the dashboard performance.",
                "Cookies: We use local storage to save your dashboard preferences (e.g., time range selection)."
            ],
            privacySection2: "2. How We Use Information",
            privacyIntro2: "We use the collected data solely to:",
            privacyList2: [
                "Access and display your channel's performance metrics.",
                "Provide AI-driven insights and predictions.",
                "Maintain and improve the stability of the Service."
            ],
            privacySection3: "3. Data Sharing & Third Parties",
            privacyIntro3: "We do not sell your personal data. Data is shared only with:",
            privacyList3: [
                "Google/YouTube: To fetch analytics data (subject to Google's Privacy Policy).",
                "AI Providers: Anonymized metrics may be processed by AI models (e.g., Google Gemini) to generate insights."
            ],

            // ToS Content
            tosIntro: "Welcome to AI Sound Lab. By accessing or using our Dashboard, you agree to be bound by these Terms of Service.",
            tosSection1: "1. Use of Service",
            tosContent1: "You agree to use this Service only for lawful purposes relevant to monitoring and analyzing YouTube channel content. You must not use this Service to violate YouTube's Terms of Service or any applicable laws.",
            tosSection2: "2. API Clients",
            tosContent2: "This Service uses YouTube API Services. By using this Service, you are also bound by the YouTube Terms of Service and Google Privacy Policy.",
            tosSection3: "3. Disclaimer of Warranties",
            tosContent3: 'The Service is provided "AS IS" and "AS AVAILABLE" without any warranties of any kind. We do not guarantee that the data predictions will be 100% accurate or that the Service will be uninterrupted.',
            tosSection4: "4. Limitation of Liability",
            tosContent4: "In no event shall AI Sound Lab be liable for any indirect, incidental, special, or consequential damages arising out of your use of the Service."
        }
    },
    kr: {
        // Build & Meta
        title: "AI 사운드 랩",
        subtitle: "채널 성과 분석 및 전략 관리",
        lastUpdated: "최근 업데이트:",
        loading: "대시보드 데이터 로딩 중...",
        sectionComingSoon: "준비 중입니다...",

        // Navigation
        nav: {
            dashboard: "대시보드",
            content: "콘텐츠",
            analytics: "미래 예측",
            earn: "수익 창출",
            customization: "맞춤 설정"
        },

        // Subtitles for each section
        subtitles: {
            dashboard: "채널 성과 분석 및 전략 관리",
            contents: "동영상 라이브러리 및 메타데이터를 효율적으로 관리하세요.",
            analytics: "AI 예측을 통해 향후 30일간의 채널 성장을 미리 확인하세요."
        },

        // Time Ranges
        timeRange: {
            daily: "최근 30일",
            weekly: "최근 30주",
            monthly: "최근 30개월"
        },

        // Stats Cards
        stats: {
            subscribers: "구독자 수",
            views: "전체 조회수",
            revenue: "예상 수익",
            watchTime: "시청 시간 (시간)",
            engagement: "참여율"
        },

        // Dashboard Section
        sections: {
            growth: "성장 추이",
            performance: "채널 성과",
            aiInsights: "AI 전략 분석",
            aiForecast: "미래 성장 전략", // New key
            aiSubtitle: "예측된 성장 데이터를 기반으로 분석된 전략입니다.",
            aiRec: "추천 전략",
            detailedAnalytics: "30일 성장 예측", // Renamed
            predictionDisclaimer: "현재 트렌드 분석 데이터를 기반으로 한 30일 예측치입니다.", // New key
            topVideos: "콘텐츠",
            noData: "이 기간에 대한 상세 데이터가 없습니다.",
            noDataSub: "유튜브 개인정보 보호 정책으로 인해 일일 데이터가 숨겨졌을 수 있습니다."
        },

        // Dropdowns
        metrics: {
            views: "조회수",
            watchTime: "시청 시간",
            subscribers: "구독자",
            revenue: "수익",
            likes: "좋아요",
            dislikes: "싫어요",
            engagement: "참여도"
        },
        predictionModels: {
            ma: "단순 이동 평균 (Simple MA)",
            wma: "가중 이동 평균 (Weighted MA - 기본값)",
            xgboost: "XGBoost (AI 예측)"
        },
        chartType: {
            changes: "변화량",
            cumulative: "누적"
        },
        videoLimit: {
            all: "전체"
        },

        // Table Headers
        table: {
            image: "썸네일",
            video: "동영상",
            id: "ID",
            views: "조회수",
            likes: "좋아요",
            dislikes: "싫어요",
            revenue: "수익"
        },

        // Footer & Legal
        footer: {
            copyright: "© 2025 AI Sound Lab. All rights reserved.",
            privacy: "개인정보처리방침",
            tos: "이용약관",
            close: "닫기"
        },

        // Legal Content Titles
        legal: {
            privacyTitle: "개인정보처리방침",
            tosTitle: "이용약관",
            lastUpdated: "최종 업데이트: 2025년 12월 21일",
            effectiveDate: "시행일: 2025년 12월 21일",

            // Privacy Content
            privacyIntro: 'AI 사운드 랩(이하 "회사")은 귀하의 개인정보를 소중하게 생각합니다. 본 방침은 귀하가 YouTube 분석 대시보드("서비스")를 이용할 때 수집되는 정보와 그 보호 방법을 설명합니다.',
            privacySection1: "1. 수집하는 정보",
            privacyList1: [
                "YouTube 데이터: YouTube Data API 및 Analytics API를 통해 채널의 공개/비공개 데이터(조회수, 구독자, 수익 등)에 접근합니다.",
                "사용 데이터: 대시보드 성능 개선을 위해 익명의 사용 통계를 수집할 수 있습니다.",
                "쿠키: 대시보드 설정(예: 시간 범위 선택) 저장을 위해 로컬 스토리지를 사용합니다."
            ],
            privacySection2: "2. 정보 사용 목적",
            privacyIntro2: "수집된 데이터는 오직 다음 목적을 위해서만 사용됩니다:",
            privacyList2: [
                "채널 성과 지표 조회 및 표시",
                "AI 기반 인사이트 및 예측 제공",
                "서비스 안정성 유지 및 개선"
            ],
            privacySection3: "3. 데이터 공유 및 제3자 제공",
            privacyIntro3: "우리는 귀하의 개인정보를 판매하지 않습니다. 데이터는 다음과 같이 공유될 수 있습니다:",
            privacyList3: [
                "Google/YouTube: 분석 데이터를 가져오기 위해 공유됩니다 (Google 개인정보처리방침 적용).",
                "AI 제공자: 익명화된 지표는 인사이트 생성을 위해 AI 모델(예: Google Gemini)에서 처리될 수 있습니다."
            ],

            // ToS Content
            tosIntro: "AI 사운드 랩에 오신 것을 환영합니다. 대시보드에 접속하거나 이를 이용함으로써 귀하는 본 이용약관에 동의하게 됩니다.",
            tosSection1: "1. 서비스 이용",
            tosContent1: "귀하는 YouTube 채널 콘텐츠 모니터링 및 분석과 관련된 합법적인 목적으로만 본 서비스를 이용해야 합니다. YouTube의 이용약관이나 관련 법규를 위반하는 용도로 서비스를 사용해서는 안 됩니다.",
            tosSection2: "2. API 클라이언트",
            tosContent2: "본 서비스는 YouTube API 서비스를 사용합니다. 본 서비스를 이용함으로써 귀하는 YouTube 이용약관 및 Google 개인정보처리방침을 준수할 것에 동의하는 것으로 간주됩니다.",
            tosSection3: "3. 보증의 부인",
            tosContent3: '본 서비스는 "있는 그대로", "이용 가능한 상태로" 제공되며, 어떠한 종류의 보증도 제공하지 않습니다. 우리는 데이터 예측의 100% 정확성이나 서비스의 무중단 운영을 보장하지 않습니다.',
            tosSection4: "4. 책임의 제한",
            tosContent4: "AI 사운드 랩은 귀하의 서비스 이용으로 인해 발생하는 어떠한 간접적, 부수적, 특별 또는 결과적 손해에 대해서도 책임을 지지 않습니다."
        }
    }
};

export type Language = 'en' | 'kr';
