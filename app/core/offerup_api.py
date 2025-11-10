# app/core/offerup_api.py
import logging
import uuid
import datetime
from typing import Dict, Any, Optional
import random
import string

import aiohttp
from aiohttp_socks import ProxyConnector

from config import MAIN_PROXY, OFFERUP_APP_VERSION, OFFERUP_BUILD

logger = logging.getLogger(__name__)


class OfferUpAPI:
    BASE_URL = "https://client-graphql.offerup.com/"

    def __init__(
            self,
            proxy: str,
            session_id: Optional[str] = None,
            device_id: Optional[str] = None,
            advertising_id: Optional[str] = None,
            user_agent: Optional[str] = None,
            browser_user_agent: Optional[str] = None):

        connector = ProxyConnector.from_url(proxy)
        self._session = aiohttp.ClientSession(connector=connector)

        # Генерация уникальных данных для аккаунта/сессии
        self.session_id = session_id or self._build_session_id()
        self.device_id = device_id or str(uuid.uuid4()).replace("-", "")[:-16]
        self.advertising_id = advertising_id or str(uuid.uuid4())
        self.user_agent, self.browser_user_agent = user_agent, browser_user_agent
        if not self.user_agent:
            self.user_agent, self.browser_user_agent = self.generate_random_user_agent()
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def _get_common_headers(self) -> Dict[str, str]:
        """
        Возвращает общие заголовки, которые требуются для большинства запросов.
        """
        headers = {
            "accept": "*/*",
            "user-agent": self.user_agent,
            "x-ou-version": OFFERUP_APP_VERSION,
            "x-ou-device-timezone": "America/New_York",
            "x-ou-d-token": self.device_id,
            "Content-Type": "application/json",
            "Host": "client-graphql.offerup.com",
            # Примеры других постоянных заголовков из запросов
            "ou-do-not-sell": "false",
            "ou-device-advertising-id": self.advertising_id,
            "ou-browser-user-agent": self.browser_user_agent,
        }
        return headers

    def _get_authenticated_headers(self) -> Dict[str, str]:
        """
        Возвращает заголовки, требующие аутентификации (JWT токен).
        """
        headers = self._get_common_headers()
        if self.jwt_token:
            headers["authorization"] = f"Bearer {self.jwt_token}"
            headers["x-ou-auth-token"] = "dummy"
        return headers

    @staticmethod
    def _build_session_id() -> str:
        session_uuid = str(uuid.uuid4())
        timestamp = str(int(datetime.datetime.now().timestamp() * 1000))  # Текущее время в миллисекундах
        return f"{session_uuid}@{timestamp}"

    @staticmethod
    def generate_random_user_agent() -> tuple[str, str]:
        """
        Генерирует случайный, но реалистичный User-Agent для Android-устройства.
        Возвращает строку User-Agent и строку ou-browser-user-agent.
        """
        # Исторические версии Android и Chrome
        android_versions = [
            "10", "11", "12", "13", "14"
        ]
        chrome_versions = [
            "110.0.5481.154", "111.0.5563.116", "112.0.5615.135", "113.0.5672.164",
            "114.0.5735.196", "115.0.5790.166", "116.0.5845.164", "117.0.5938.140",
            "118.0.5993.111", "119.0.6045.163", "120.0.6099.144", "121.0.6167.143",
            "122.0.6261.148", "123.0.6312.121", "124.0.6367.179", "125.0.6422.140",
            "126.0.6478.122", "127.0.6553.150", "128.0.6613.147", "129.0.6668.150",
            "130.0.6723.103", "131.0.6778.139", "132.0.6834.139", "133.0.6893.109",
            "134.0.6957.109", "135.0.7022.139", "136.0.7088.109", "137.0.7154.140",
            "138.0.7220.140", "139.0.7286.140", "140.0.7339.51"
        ]
        # Популярные модели устройств
        device_models = [
            "SM-G973F", "SM-G988B", "SM-G998B", "SM-G991B", "SM-G996B", "SM-G990E",
            "SM-N986B", "SM-N981B", "SM-F711B", "SM-F916B", "SM-A515F", "SM-A528B",
            "SM-A715F", "SM-A325F", "SM-A127F", "SM-A037F", "SM-A025F", "SM-A013F"
        ]

        android_version = random.choice(android_versions)
        chrome_version = random.choice(chrome_versions)
        device_model = random.choice(device_models)
        build_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        # Собираем User-Agent
        ua = f"OfferUp/{OFFERUP_APP_VERSION} (build: {OFFERUP_BUILD}; samsung {device_model} {build_id}; Android {android_version}; en_US)"
        browser_ua = f"Mozilla/5.0 (Linux; Android {android_version}; {device_model} Build/{build_id}; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/{chrome_version} Mobile Safari/537.36"

        return ua, browser_ua

    async def _make_request(self, operation_name: str, query: str, variables: Dict[str, Any] = None,
                            requires_auth: bool = False, screen: str = "",
                            additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Внутренный метод для выполнения GraphQL-запросов.
        Автоматически генерирует x-request-id и обновляет x-ou-usercontext, если он изменился.
        Правильно сохраняет и использует куки между запросами.

        Args:
            operation_name (str): Имя операции GraphQL.
            query (str): GraphQL-запрос.
            variables (Dict[str, Any], optional): Переменные для GraphQL-запроса.
            requires_auth (bool): Требуется ли аутентификация для запроса.
            screen (str): Значение для заголовка x-ou-screen.
            additional_headers (Optional[Dict[str, str]]): Дополнительные заголовки для конкретного вызова.

        Returns:
            Dict[str, Any]: JSON-ответ от API.
        """
        headers = self._get_authenticated_headers() if requires_auth else self._get_common_headers()
        headers.update(additional_headers or {})
        headers.update({
            "x-ou-operation-name": operation_name,
            "x-ou-session-id": self.session_id,
            "x-ou-usercontext": "{}",
            "x-ou-screen": screen,
            "x-request-id": str(uuid.uuid4()),
        })
        # if self.cookies:
        #     headers.update({
        #         "Cookie": "; ".join(
        #             [f"{key}={value}" for key, value in self.cookies.items()]
        #         )
        #     })

        payload = {
            "operationName": operation_name,
            "query": query.replace("  ", ""),  # Уберём лишние отступы
        }
        if variables is not None:
            payload["variables"] = variables

        # logger.debug(f"Отправляю запрос по {self.BASE_URL}\nЗаголовки: {headers}\nТело: {payload}")

        try:
            async with self._session.post(self.BASE_URL, headers=headers, json=payload) as response:
                response.raise_for_status()  # Вызовет исключение для 4xx/5xx
                response_json = await response.json()
                # logger.debug(f"Ответ на запрос OfferUpAPI: {response_json}\nЗаголовки ответа: {response.headers}")
                return response_json
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

    # --- API Методы ---

    async def get_user_context(self, viewport_size: Dict[str, int], search_location: Dict[str, float]) -> Dict[str, Any]:
        """
        Получает контекст пользователя.
        Этот вызов обновляет self._user_context.
        """
        query = """
        query GetUserContext($input: UserContextInput) {
          userContext(input: $input) {
            ...userContext
            __typename
          }
        }

        fragment userContext on UserContextResponse {
          userContext {
            key
            value
            __typename
          }
          __typename
        }
        """
        variables = {
            "input": {
                "viewportSize": viewport_size,
                "searchLocation": search_location
            }
        }
        response = await self._make_request(
            "GetUserContext",
            query,
            variables,
            requires_auth=False,
            screen="OnboardingBuyerInterestSelection"
        )

        if response and 'data' in response and 'userContext' in response['data']:  # Обновляем внутренний user_context из ответа
            self.user_context = response['data']['userContext'].get('userContext', {})
        return response

    async def signup(self, email: str, name: str, password: str, client_type: str = "Android") -> Dict[str, Any]:
        """
        Регистрация нового пользователя.
        """
        query = """
        mutation Signup($email: String!, $name: String!, $password: String!, $clientType: String) {
          signup(
            data: {email: $email, name: $name, password: $password, clientType: $clientType}
          ) {
            id
            profile {
              name
              firstName
              lastName
              ratingSummary {
                average
                count
                __typename
              }
              avatars {
                xlImage
                useDefaultAvatar
                __typename
              }
              dateJoined
              publicLocationName
              isAutosDealer
              isBusinessAccount
              isTruyouVerified
              truYouVerificationStatus
              isPhoneNumberVerified
              isEmailVerified
              phoneNumber
              isSubPrimeDealer
              followers
              following
              chatFeatures {
                canUseP2P
                __typename
              }
              __typename
            }
            account {
              email
              facebookId
              isTermsAccepted
              isPremium
              __typename
            }
            sessionToken {
              value
              __typename
            }
            refreshToken {
              value
              __typename
            }
            djangoToken {
              value
              __typename
            }
            __typename
          }
        }
        """
        variables = {
            "email": email,
            "name": name,
            "password": password,
            "clientType": client_type
        }
        response = await self._make_request(
            "Signup", query, variables, requires_auth=False, screen="/auth-stack/signup")
        return response

    async def get_auth_user(self) -> Dict[str, Any]:
        """
        Получает данные авторизованного пользователя.
        """
        query = """
        query GetAuthUser {
          me {
            ...me
            __typename
          }
        }

        fragment me on User {
          id
          profile {
            userId
            name
            firstName
            ratingSummary {
              average
              count
              __typename
            }
            avatars {
              xlImage
              squareImage
              useDefaultAvatar
              __typename
            }
            avatarBadges {
              primaryBadge
              secondaryBadge
              __typename
            }
            dateJoined
            publicLocationName
            location {
              name
              publicName
              verified
              latitude
              longitude
              __typename
            }
            isAutosDealer
            isBusinessAccount
            businessAccountId
            isTruyouVerified
            truYouVerificationStatus
            isPhoneNumberVerified
            isEmailVerified
            phoneNumber
            isSubPrimeDealer
            followers
            following
            dailyStreak
            chatFeatures {
              canUseP2P
              __typename
            }
            profileFeatures {
              canViewBusinessInfoInProfilePage
              canViewItemsFromThisSeller
              canViewStoreInventory
              __typename
            }
            __typename
          }
          account {
            email
            facebookId
            isTermsAccepted
            isPremium
            isPremiumFreeTrialAvailable
            __typename
          }
          userCapabilities {
            canAccessBusinessPortal
            canAccessBusinessTools
            canAccessPromotionResultOrItemPerformance
            canSellAnotherListing
            canSendPhotosInChat
            canSendQuickReplies
            hasAfterHoursAutoResponder
            hasVerifiedBadge
            verifiedBadgeType
            __typename
          }
          __typename
        }
        """
        return await self._make_request("GetAuthUser", query, requires_auth=True, screen="/accountstack/account")

    async def get_unread_alert_count(self) -> Dict[str, Any]:
        """
        Получает количество непрочитанных уведомлений.
        """
        query = """
        query GetUnreadAlertCount {
          unreadNotificationCount {
            total
            inbox
            notifications
            __typename
          }
        }
        """
        return await self._make_request(
            "GetUnreadAlertCount", query, requires_auth=True, screen="/accountstack/account")

    async def change_email(self, user_id: int, email: str) -> Dict[str, Any]:
        """
        Изменяет email пользователя.
        """
        query = """
        mutation ChangeEmail($userId: ID!, $email: String!, $multifactorHeaderInfo: MultifactorHeaderInfo) {
          changeEmail(
            data: {userId: $userId, email: $email, multifactorHeaderInfo: $multifactorHeaderInfo}
          )
        }
        """
        variables = {
            "userId": user_id,
            "email": email
        }
        return await self._make_request(
            "ChangeEmail", query, variables, requires_auth=True, screen="/verify-email-stack/verify-email")

    async def confirm_email_from_token(self, user_id: str, token: str) -> Dict[str, Any]:
        """
        Подтверждает email, используя userId и token из письма.
        Выполняет GraphQL-запрос ConfirmEmail.
        Требует аутентификации (JWT токен).
        """
        query = """
        mutation ConfirmEmail($userId: ID!, $token: String!, $challengeId: ID) {
          confirmEmail(data: {userId: $userId, token: $token, challengeId: $challengeId})
        }
        """
        variables = {
            "userId": user_id,
            "token": token,
            "challengeId": None  # challenge_id из URL в примере был пустым, передаём null
        }
        return await self._make_request(
            "ConfirmEmail", query, variables, requires_auth=True, screen="/verify-email-stack/verify-email")

    async def get_item_detail_data_by_listing_id(self, listing_id: str, is_logged_in: bool = False,
                                                 device_location: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Получает детали товара по его идентификатору.
        """
        query = """
        query GetItemDetailDataByListingId($listingId: ID!, $isLoggedIn: Boolean = false, $deviceLocation: DeviceLocation) {
          listing(listingId: $listingId, deviceLocation: $deviceLocation) {
            ...ItemDetailData
            __typename
          }
        }

        fragment ListingData on Listing {
          id
          listingId
          additionalDetails {
            key
            value
            __typename
          }
          availabilityConfirmedAt
          condition
          conditionDisplayText
          description
          details {
            key
            value
            __typename
          }
          fulfillmentDetails {
            buyItNowEnabled
            canShipToBuyer
            isFreeShipping
            localPickupEnabled
            shippingEnabled
            shippingPrice
            shippingType
            showBuyNow
            __typename
          }
          isFirmOnPrice
          isLocal
          isAutosPost
          isSold
          isUnlisted
          isRemoved
          lastEdited
          listingCategory {
            id
            categoryAttributeMap {
              attributeName
              attributeUILabel
              attributeValue
              __typename
            }
            categoryV2 {
              id
              l1Name
              l2Name
              __typename
            }
            __typename
          }
          locationDetails {
            latitude
            locationName
            longitude
            zipcode
            __typename
          }
          originalPrice
          owner {
            id
            profile {
              avatars {
                squareImage
                __typename
              }
              businessInfo {
                openingHours {
                  day
                  hours
                  __typename
                }
                publicLocation {
                  formattedAddress
                  __typename
                }
                externalReviews {
                  average
                  googleReviewsReadMoreUrl
                  __typename
                }
                __typename
              }
              clickToCallEnabled
              dateJoined
              isAutosDealer
              isBusinessAccount
              isSubPrimeDealer
              isTruyouVerified
              lastActive
              name
              notActive
              ratingSummary {
                average
                count
                __typename
              }
              reviews {
                average
                __typename
              }
              sellerType
              websiteLink
              profileFeatures {
                canClickToCall
                canViewItemsFromThisSeller
                canViewStoreInventory
                canViewExternalReviews
                __typename
              }
              __typename
            }
            __typename
          }
          ownerId
          photos {
            uuid
            detailFull {
              url
              width
              height
              __typename
            }
            detailSquare {
              uuid
              height
              url
              width
              __typename
            }
            __typename
          }
          postDate
          price
          saved @include(if: $isLoggedIn)
          title
          vehicleAttributes {
            vehicleCityMpg
            vehicleEpaCity
            vehicleEpaHighway
            vehicleExternalHistoryReport {
              epochDate
              imageUrl
              issues
              price {
                microUnits
                __typename
              }
              providerName
              reportUrl
              __typename
            }
            vehicleFundamentals
            vehicleHighwayMpg
            vehicleMake
            vehicleMiles
            vehicleModel
            vehicleVin
            vehicleYear
            __typename
          }
          __typename
        }

        fragment ItemDetailData on Listing {
          ...ListingData
          formattedOriginalPrice
          formattedPrice
          isOwnItem
          priceDropPercentage
          showOriginalPrice
          isGoodDeal
          externalCheckoutDetails {
            extMerchantCheckoutUrl
            extMerchantMarketplaceType
            extMerchantProductId
            extMerchantStore
            __typename
          }
          __typename
        }
        """
        variables = {
            "listingId": listing_id,
            "isLoggedIn": is_logged_in,
            "deviceLocation": device_location
        }
        # screen зависит от контекста вызова, используем общий
        return await self._make_request(
            "GetItemDetailDataByListingId", query, variables, requires_auth=is_logged_in, screen="ItemDetail")

    async def public_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Получает публичный профиль пользователя.
        """
        query = """
        query PublicProfile($userId: Int, $vanityUserId: ID) {
          publicProfile(userId: $userId, vanityUserId: $vanityUserId) {
            userId
            avatars {
              xlImage
              squareImage
              __typename
            }
            avatarBadges {
              primaryBadge
              secondaryBadge
              __typename
            }
            isTruyouVerified
            name
            dateJoined
            publicLocationName
            responseTime
            ratingSummary {
              count
              average
              __typename
            }
            itemsSold
            itemsPurchased
            ratingAttributes {
              count
              value
              __typename
            }
            badges {
              label
              icon
              __typename
            }
            bio
            featureAttributes {
              clickToCallEnabled
              __typename
            }
            profileFeatures {
              canViewItemsFromThisSeller
              canViewProfileBio
              canViewStoreInventory
              canViewBusinessInfoInProfilePage
              canClickToCall
              canViewExternalReviews
              __typename
            }
            c2cPhoneNumber {
              countryCode
              nationalNumber
              __typename
            }
            isAutosDealer
            isBusinessAccount
            isSubPrimeDealer
            isTruyouVerified
            isPremium
            websiteLink
            publicLocation {
              formattedAddress
              name
              latitude
              longitude
              __typename
            }
            openingHours {
              day
              hours
              __typename
            }
            reviews {
              average
              attributionIcon
              googleReviewsReadMoreUrl
              title
              userReviews {
                text
                profilePhotoUrl
                __typename
              }
              __typename
            }
            notActive
            followers
            following
            isFollowedByMe
            lastActive
            chatFeatures {
              canUseP2P
              __typename
            }
            businessInfo {
              externalReviews {
                average
                googleReviewsReadMoreUrl
                __typename
              }
              __typename
            }
            __typename
          }
        }
        """
        variables = {"userId": user_id}
        return await self._make_request(
            "PublicProfile", query, variables, requires_auth=True, screen="PublicProfile")

    async def get_inbox_alerts(self, alert_type: str = "INBOX") -> Dict[str, Any]:
        """
        Получает уведомления из "входящих".
        """
        query = """
        query GetInboxAlerts($input: InboxAlertsInput!) {
          inboxAlerts(input: $input) {
            alerts {
              ...chatAlert
              ...baseBingAd
              ...baseGoogleDisplayAd
              ... on Alert {
                alertRows {
                  ...chatAlert
                  __typename
                }
                __typename
              }
              __typename
            }
            pinnedAlerts {
              ...chatAlert
              __typename
            }
            groupOptions {
              isSelected
              label
              optionKey
              __typename
            }
            sortOptions {
              isSelected
              label
              optionKey
              __typename
            }
            telemetryData {
              rawNotificationCount
              parsedNotificationCount
              processedNotificationCount
              __typename
            }
            __typename
          }
        }

        fragment chatAlert on Alert {
          id
          actionPath
          contentThumbnails
          dateAdded
          displayAvatar
          eventMetadata
          notificationSource
          notificationText
          objectId
          pinned
          read
          seen
          sender {
            id
            profile {
              avatars {
                squareImage
                __typename
              }
              firstName
              isAutosDealer
              isBusinessAccount
              isPremium
              isTruyouVerified
              notActive
              avatarBadges {
                primaryBadge
                secondaryBadge
                __typename
              }
              __typename
            }
            __typename
          }
          title
          type
          visualTags {
            displayText
            tag
            type
            __typename
          }
          listingId
          __typename
        }

        fragment baseBingAd on BingAd {
          ouAdId
          adExperimentId
          adMediationId
          adNetwork
          adRequestId
          adSettings {
            repeatClickRefractoryPeriodMillis
            collapsible
            __typename
          }
          bingClientId
          clickFeedbackUrl
          clickReturnUrl
          contentUrl
          deepLinkEnabled
          experimentDataHash
          imageUrl
          impressionFeedbackUrl
          impressionUrls
          viewableImpressionUrls
          installmentInfo {
            amount
            description
            downPayment
            __typename
          }
          itemName
          lowPrice
          price
          sellerName
          templateFields {
            key
            value
            __typename
          }
          type
          __typename
        }

        fragment baseGoogleDisplayAd on GoogleDisplayAd {
          ouAdId
          adExperimentId
          adHeight
          adMediationId
          adNetwork
          adRequestId
          adWidth
          adaptive
          clickFeedbackUrl
          clientId
          contentUrl
          customTargeting {
            key
            values
            __typename
          }
          displayAdType
          formatIds
          errorDrawable {
            actionPath
            listImage {
              height
              url
              width
              __typename
            }
            __typename
          }
          experimentDataHash
          impressionFeedbackUrl
          personalizationProperties {
            key
            values
            __typename
          }
          prebidConfigs {
            key
            values {
              timeout
              tamSlotUUID
              liftoffPlacementIDs
              nimbusPriceMapping
              adPosition
              __typename
            }
            __typename
          }
          adSettings {
            repeatClickRefractoryPeriodMillis
            timeout
            collapsible
            __typename
          }
          type
          __typename
        }
        """
        variables = {"input": {"type": alert_type}}
        return await self._make_request(
            "GetInboxAlerts", query, variables, requires_auth=True, screen="Inbox")

    async def get_chat_discussion(self, listing_id: str, discussion_id: str = None) -> Dict[str, Any]:
        """
        Получает историю чата по идентификатору лота и/или обсуждения.
        """
        query = """
        query GetChatDiscussion($input: ChatDiscussionInput!) {
          chatDiscussion(input: $input) {
            buyerProfile {
              phoneNumber
              email
              name
              __typename
            }
            isAllowedInteraction
            suggestedMessages {
              id
              text
              __typename
            }
            discussion {
              id
              itemId
              listingId
              sellerId
              buyerId
              dateCreated
              lastPostDate
              readStatus {
                userId
                lastReadDate
                __typename
              }
              visualTags {
                tag
                type
                displayText
                __typename
              }
              shippingSummary {
                buyerId
                canSendPhotos
                itemId
                listingId
                paymentId
                paymentUUID
                sellerId
                shippingContext {
                  availableBuyerDiscounts {
                    buyerDiscountAmount
                    buyerDiscountTypeName
                    expiresAt
                    __typename
                  }
                  buyNowEnabled
                  canShipToBuyer
                  shippingCost
                  shippingDeadline
                  __typename
                }
                __typename
              }
              messages {
                id
                recipientId
                senderId
                text
                sendDateString
                reaction
                metadataType
                metadata {
                  systemMessageContext {
                    iconUrl
                    actions {
                      actionPath
                      externalURL
                      actionText
                      __typename
                    }
                    titleText
                    bodyText
                    __typename
                  }
                  place {
                    name
                    formattedAddress
                    placeId
                    longitude
                    latitude
                    __typename
                  }
                  photos {
                    small {
                      url
                      width
                      height
                      __typename
                    }
                    medium {
                      url
                      width
                      height
                      __typename
                    }
                    large {
                      url
                      width
                      height
                      __typename
                    }
                    __typename
                  }
                  __typename
                }
                linkPreviews {
                  ...linkPreview
                  __typename
                }
                __typename
              }
              otherUserProfile {
                ...GetChatDiscussionUserProfileData
                __typename
              }
              availableReactions
              alertId
              pinned
              availablePromos {
                purchasedItemPromos {
                  isPromoted
                  __typename
                }
                itemActions {
                  itemId
                  inventoryPromos {
                    inventoryPromoId
                    currentItemId
                    currentItemTitle
                    promoType
                    __typename
                  }
                  promos {
                    subtitleToDisplay
                    decoratorToDisplay
                    title
                    preselected
                    promoType
                    featureList {
                      description
                      available
                      __typename
                    }
                    paymentDataIos {
                      sku
                      __typename
                    }
                    paymentDataAndroid {
                      sku
                      __typename
                    }
                    __typename
                  }
                  promoHierarchy {
                    title
                    subtitleToDisplay
                    decoratorToDisplay
                    freeTrialAvailable
                    preselected
                    purchasedDescriptionToDisplay
                    featureList {
                      description
                      available
                      __typename
                    }
                    __typename
                  }
                  __typename
                }
                __typename
              }
              suggestedMessages {
                id
                text
                __typename
              }
              quickReplies {
                replyId
                title
                message
                __typename
              }
              request {
                status
                recipientId
                senderId
                __typename
              }
              __typename
            }
            listing {
              id
              listingId
              title
              price
              isFirmOnPrice
              owner {
                id
                profile {
                  ...GetChatDiscussionUserProfileData
                  __typename
                }
                __typename
              }
              photos {
                uuid
                squareSmall {
                  url
                  width
                  height
                  __typename
                }
                square {
                  url
                  width
                  height
                  __typename
                }
                detailSquare {
                  url
                  width
                  height
                  __typename
                }
                small {
                  url
                  width
                  height
                  __typename
                }
                detail {
                  url
                  width
                  height
                  __typename
                }
                list {
                  url
                  width
                  height
                  __typename
                }
                __typename
              }
              fulfillmentDetails {
                buyItNowEnabled
                shippingEnabled
                localPickupEnabled
                shippingPrice
                estimatedDeliveryDateStart
                estimatedDeliveryDateEnd
                sellerPaysShipping
                shippingParcelId
                canShipToBuyer
                __typename
              }
              state
              formattedPrice
              isAutosPost
              isBuyNowEnabled
              isRemoved
              isSold
              listingCategory {
                id
                categoryV2 {
                  id
                  l1Id
                  l2Id
                  __typename
                }
                __typename
              }
              locationDetails {
                zipcode
                __typename
              }
              __typename
            }
            autosVerifiedCheckoutTransaction {
              sellerTransactionStep
              sellerTransactionSteps
              buyerTransactionStep
              buyerTransactionSteps
              landingUrl
              __typename
            }
            __typename
          }
        }

        fragment linkPreview on LinkPreview {
          title
          description
          subtext
          imageUrl
          actionPath
          originUrl
          imageOverlayText
          __typename
        }

        fragment GetChatDiscussionUserProfileData on UserProfile {
          userId
          avatars {
            squareImage
            __typename
          }
          businessInfo {
            reviews {
              average
              __typename
            }
            __typename
          }
          clickToCallEnabled
          isAutosDealer
          allowBuyerProfile: isAutosDealer
          isBusinessAccount
          isSubPrimeDealer
          isTruyouVerified
          isPremium
          lastActive
          name
          ratingSummary {
            average
            count
            __typename
          }
          sellerType
          notActive
          location {
            publicName
            __typename
          }
          profileFeatures {
            canClickToCall
            __typename
          }
          __typename
        }
        """
        # Используем discussionId, если он предоставлен, иначе только listingId
        input_vars = {"listingId": listing_id}
        if discussion_id:
            input_vars["discussionId"] = discussion_id
        variables = {"input": input_vars}
        return await self._make_request(
            "GetChatDiscussion", query, variables, requires_auth=True, screen="Discussion")

    async def post_message(self, discussion_id: str, text: str) -> Dict[str, Any]:
        """
        Отправляет сообщение в существующий чат.
        """
        query = """
        mutation PostMessage($text: String, $discussionId: String!, $photoUuids: [String!], $suggestedMessageId: String) {
          postMessage(
            data: {discussionId: $discussionId, text: $text, suggestedMessageId: $suggestedMessageId}
            photoUuids: $photoUuids
          )
        }
        """
        variables = {
            "discussionId": discussion_id,
            "text": text
        }
        return await self._make_request(
            "PostMessage", query, variables, requires_auth=True, screen="Discussion")

    async def post_first_message(self, listing_id: str, text: str) -> Dict[str, Any]:
        """
        Отправляет первое сообщение в чат по лоту, создавая обсуждение.
        """
        query = """
        mutation PostFirstMessage($input: PostFirstMessageInput!) {
          postFirstMessage(data: $input) {
            discussionId
            __typename
          }
        }
        """
        variables = {
            "input": {
                "listingId": listing_id,
                "text": text
            }
        }
        return await self._make_request(
            "PostFirstMessage", query, variables, requires_auth=True, screen="Discussion")

    async def update_read_date(self, discussion_id: str, user_id: str, last_post_date: str) -> Dict[str, Any]:
        """
        Обновляет дату последнего прочтения в чате.
        """
        query = """
        mutation UpdateReadDate($input: UpdateReadDateInput!) {
          updateReadDate(data: $input)
        }
        """
        variables = {
            "input": {
                "discussionId": discussion_id,
                "userId": user_id,
                "lastPostDate": last_post_date
            }
        }
        return await self._make_request(
            "UpdateReadDate", query, variables, requires_auth=True, screen="Discussion")

    async def change_phone_number(self, phone_number: str, country_code: int = 1) -> Dict[str, Any]:
        """
        Изменяет номер телефона пользователя.
        """
        query = """
        mutation ChangePhoneNumber($countryCode: Int!, $phoneNumber: String!) {
          changePhoneNumber(data: {countryCode: $countryCode, phoneNumber: $phoneNumber}) {
            referenceId
            __typename
          }
        }
        """
        variables = {
            "phoneNumber": phone_number,
            "countryCode": country_code
        }
        return await self._make_request(
            "ChangePhoneNumber", query, variables, requires_auth=True, screen="VerifyPhone")

    async def change_phone_number_confirm(self, otp: str, reference_id: str, phone_number: str, country_code: int = 1,
                                          challenge_id: str = None) -> Dict[str, Any]:
        """
        Подтверждает изменение номера телефона с помощью OTP-кода.
        """
        query = """
        mutation ChangePhoneNumberConfirm($otp: String!, $referenceId: String!, $countryCode: Int!, $phoneNumber: String!, $challengeId: ID) {
          changePhoneNumberConfirm(
            data: {otp: $otp, referenceId: $referenceId, countryCode: $countryCode, phoneNumber: $phoneNumber, challengeId: $challengeId}
          )
        }
        """
        variables = {
            "otp": otp,
            "referenceId": reference_id,
            "countryCode": country_code,
            "phoneNumber": phone_number
        }
        if challenge_id:
            variables["challengeId"] = challenge_id

        return await self._make_request(
            "ChangePhoneNumberConfirm", query, variables, requires_auth=True, screen="EnterCode")

    async def get_category_taxonomy(self) -> Dict[str, Any]:
        """Получает иерархию категорий OfferUp."""
        query = """
        query GetCategoryTaxonomy($input: GetTaxonomyInput) {
          getTaxonomy(input: $input) {
            ...categoryTaxonomy
            __typename
          }
        }

        fragment categoryTaxonomy on CategoryTaxonomy {
          children {
            id
            currentLevelId
            level
            label
            order
            path
            children {
              id
              currentLevelId
              level
              label
              order
              path
              children {
                id
                currentLevelId
                level
                label
                order
                path
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        """
        variables = {"input": {}}
        return await self._make_request(
            "GetCategoryTaxonomy", query, variables, requires_auth=False, screen="")

    async def get_new_listings_in_category(self, category_id: str, page_cursor: Optional[str] = None) -> Dict[str, Any]:
        query = """
        query GetModularFeed($searchParams: [SearchParam], $debug: Boolean = false) {
          modularFeed(params: $searchParams, debug: $debug) {
            ...modularFeedResponse
            __typename
          }
        }

        fragment baseFilterParams on ModularFeedBaseFilter {
          shortcutLabel
          shortcutRank
          subTitle
          targetName
          title
          type
          isExpandedHighlight
          __typename
        }

        fragment modularFilterNumericRangeBound on ModularFeedNumericRangeFilterNumericRangeBound {
          label
          limit
          placeholderText
          targetName
          value
          __typename
        }

        fragment modularFilterNumericRange on ModularFeedNumericRangeFilter {
          ...baseFilterParams
          lowerBound {
            ...modularFilterNumericRangeBound
            __typename
          }
          upperBound {
            ...modularFilterNumericRangeBound
            __typename
          }
          __typename
        }

        fragment modularFilterSelectionList on ModularFeedSelectionListFilter {
          ...baseFilterParams
          selectedValue
          showSelectAll
          options {
            isDefault
            isSelected
            label
            subLabel
            value
            __typename
          }
          __typename
        }

        fragment baseTileParams on ModularFeedTile {
          tileId
          tileType
          __typename
        }

        fragment bannerTile on ModularFeedTileBanner {
          ...baseTileParams
          title
          __typename
        }

        fragment emptyStateTile on ModularFeedTileEmptyState {
          ...baseTileParams
          title
          description
          iconType
          __typename
        }

        fragment modularFeedListing on ModularFeedListing {
          listingId
          conditionText
          flags
          image {
            height
            url
            width
            __typename
          }
          isFirmPrice
          locationName
          price
          formattedPrice
          formattedOriginalPrice
          priceDropPercentage
          title
          vehicleMiles
          __typename
        }

        fragment listingTile on ModularFeedTileListing {
          ...baseTileParams
          listing {
            ...modularFeedListing
            __typename
          }
          __typename
        }

        fragment bingAdTile on ModularFeedTileBingAd {
          ...baseTileParams
          bingAd {
            ouAdId
            adExperimentId
            adNetwork
            adRequestId
            adTileType
            adSettings {
              repeatClickRefractoryPeriodMillis
              ctaType
              ctaLabel
              collapsible
              __typename
            }
            bingClientId
            clickFeedbackUrl
            clickReturnUrl
            contentUrl
            deepLinkEnabled
            experimentDataHash
            image {
              height
              url
              width
              __typename
            }
            impressionFeedbackUrl
            impressionUrls
            viewableImpressionUrls
            installmentInfo {
              amount
              description
              downPayment
              __typename
            }
            itemName
            lowPrice
            price
            searchId
            sellerName
            templateFields {
              key
              value
              __typename
            }
            __typename
          }
          __typename
        }

        fragment AdSettingFields on AdSettings {
          repeatClickRefractoryPeriodMillis
          timeout
          collapsible
          loadStrategy
          reloadEnabled
          reloadCount
          __typename
        }

        fragment googleDisplayAdTile on ModularFeedTileGoogleDisplayAd {
          ...baseTileParams
          googleDisplayAd {
            ouAdId
            additionalSizes
            adExperimentId
            adHeight
            adNetwork
            adPage
            adRequestId
            adSettings {
              ...AdSettingFields
              __typename
            }
            adTileType
            adWidth
            adaptive
            channel
            clickFeedbackUrl
            clientId
            contentUrl
            neighboringContentUrls
            customTargeting {
              key
              values
              __typename
            }
            displayAdType
            errorDrawable {
              actionPath
              listImage {
                height
                url
                width
                __typename
              }
              __typename
            }
            experimentDataHash
            formatIds
            impressionFeedbackUrl
            personalizationProperties {
              key
              values
              __typename
            }
            prebidConfigs {
              key
              values {
                timeout
                tamSlotUUID
                liftoffPlacementIDs
                nimbusPriceMapping
                adPosition
                __typename
              }
              __typename
            }
            renderLocation
            searchId
            searchQuery
            templateId
            __typename
          }
          __typename
        }

        fragment localDisplayAdTile on ModularFeedTileLocalDisplayAd {
          ...baseTileParams
          localDisplayAd {
            ouAdId
            adExperimentId
            adNetwork
            adRequestId
            adTileType
            advertiserId
            businessName
            callToAction
            callToActionType
            clickFeedbackUrl
            contentUrl
            experimentDataHash
            headline
            image {
              height
              url
              width
              __typename
            }
            impressionFeedbackUrl
            searchId
            __typename
          }
          __typename
        }

        fragment adsPostXAdTile on ModularFeedTileAdsPostXAd {
          ...baseTileParams
          adsPostXAd {
            ouAdId
            adExperimentId
            adNetwork
            adRequestId
            adTileType
            clickFeedbackUrl
            experimentDataHash
            impressionFeedbackUrl
            searchId
            offer {
              beacons {
                noThanksClick
                close
                __typename
              }
              title
              description
              clickUrl
              image
              pixel
              ctaYes
              ctaNo
              __typename
            }
            __typename
          }
          __typename
        }

        fragment customNativeAdTile on ModularFeedTileCustomNativeAd {
          ...baseTileParams
          customNativeAd {
            ouAdId
            adExperimentId
            adNetwork
            adRequestId
            adTileType
            clickFeedbackUrl
            experimentDataHash
            impressionFeedbackUrl
            searchId
            templateId
            type
            tileType
            clickThroughUrl
            adSettings {
              repeatClickRefractoryPeriodMillis
              collapsible
              __typename
            }
            eventUrls {
              eventType
              urls
              __typename
            }
            metadata {
              key
              value
              __typename
            }
            templateData {
              key
              value
              __typename
            }
            templateFields {
              key
              value
              __typename
            }
            __typename
          }
          __typename
        }

        fragment linkPreview on LinkPreview {
          title
          description
          subtext
          imageUrl
          actionPath
          originUrl
          imageOverlayText
          __typename
        }

        fragment communityPollOption on CommunityPollOption {
          value
          count
          userSelected
          __typename
        }

        fragment communityPoll on CommunityPoll {
          id
          hasVotedPoll
          totalCount
          options {
            ...communityPollOption
            __typename
          }
          __typename
        }

        fragment communityPost on CommunityPost {
          id
          parentId
          postDate
          title
          description
          upVoteCount
          replyCount
          hasUpVoted
          hasSaved
          poster {
            userId
            name
            publicLocationName
            avatars {
              squareImage
              __typename
            }
            avatarBadges {
              primaryBadge
              secondaryBadge
              __typename
            }
            notActive
            __typename
          }
          linkPreviews {
            titleLinkPreviews {
              ...linkPreview
              __typename
            }
            descriptionLinkPreviews {
              ...linkPreview
              __typename
            }
            __typename
          }
          pollResults {
            ...communityPoll
            __typename
          }
          __typename
        }

        fragment communityPostTile on ModularFeedTileCommunityPost {
          ...baseTileParams
          post {
            ...communityPost
            __typename
          }
          __typename
        }

        fragment couponTile on ModularFeedTileCoupon {
          tileId
          tileType
          coupon {
            id
            businessName
            categoryId
            businessId
            endDate
            logoImg
            locations {
              id
              latitude
              longitude
              formattedAddress
              street
              city
              state
              zipCode
              phone
              __typename
            }
            offers {
              id
              detail
              expDate
              disclaimer
              __typename
            }
            __typename
          }
          __typename
        }

        fragment jobTile on ModularFeedTileJob {
          ...baseTileParams
          job {
            address {
              city
              state
              zipcode
              __typename
            }
            companyName
            datePosted
            image {
              height
              url
              width
              __typename
            }
            industry
            jobId
            jobListingUrl
            jobOwnerId
            pills {
              text
              type
              __typename
            }
            title
            apply {
              method
              value
              __typename
            }
            wageDisplayValue
            provider
            __typename
          }
          __typename
        }

        fragment localEvent on LocalEvent {
          id
          ownerId
          title
          startDate
          endDate
          timeZone
          neighborhood
          pills
          category
          categories
          feedImageUrl
          formattedDate {
            time
            month
            dayOfMonth
            dayOfWeek
            date
            isToday
            __typename
          }
          __typename
        }

        fragment localEventTile on ModularFeedTileLocalEvent {
          tileId
          tileType
          localEvent {
            ...localEvent
            __typename
          }
          __typename
        }

        fragment sellerAdTile on ModularFeedTileSellerAd {
          ...baseTileParams
          listing {
            ...modularFeedListing
            __typename
          }
          sellerAd {
            ouAdId
            adId
            adExperimentId
            adNetwork
            adRequestId
            adTileType
            clickFeedbackUrl
            experimentDataHash
            impressionFeedbackUrl
            impressionUrls
            searchId
            __typename
          }
          __typename
        }

        fragment rentalTile on ModularFeedTileRental {
          tileId
          tileType
          rental {
            name
            id
            rent
            bedrooms
            bathrooms
            additionalUnits {
              id
              __typename
            }
            image {
              id
              thumbnail
              detail
              __typename
            }
            property {
              id
              name
              location {
                latitude
                longitude
                __typename
              }
              address {
                street
                city
                state
                zipCode
                __typename
              }
              __typename
            }
            floorPlan {
              id
              squareFeet
              __typename
            }
            partner
            __typename
          }
          __typename
        }

        fragment searchAlertTile on ModularFeedTileSearchAlert {
          ...baseTileParams
          title
          __typename
        }

        fragment serviceTile on ServiceListing {
          id
          businessName
          businessLocation
          yearsInBusiness
          numberOfHires
          numberOfEmployees
          hasBackgroundCheck
          licenseVerified
          isTopPro
          rating {
            key
            value
            formatted
            label
            __typename
          }
          numReviews
          reviews
          serviceReviews {
            author
            profileImage
            rating
            text
            createdDate
            __typename
          }
          reviewsSource
          featuredReview
          description
          imageUrl
          backgroundImageUrl
          location
          pills {
            key
            label
            __typename
          }
          responseTimeHours
          quote {
            startingCost
            costUnit
            label
            __typename
          }
          additionalDetails {
            key
            label
            __typename
          }
          categoryName
          __typename
        }

        fragment thumbtackServiceTile on ModularFeedTileThumbtackService {
          ...baseTileParams
          thumbtackService {
            ...serviceTile
            iframeUrl
            __typename
          }
          __typename
        }

        fragment inHouseServiceTile on ModularFeedTileInHouseService {
          ...baseTileParams
          inHouseService {
            ...serviceTile
            ownerId
            subcategories
            projectImages {
              id
              url
              width
              height
              __typename
            }
            businessVerified
            __typename
          }
          __typename
        }

        fragment localNews on LocalNews {
          URL
          formattedDate
          id
          imageURL
          score
          sentimentNegative
          sentimentNeutral
          sentimentPositive
          source
          sourceCity
          summary
          title
          topics
          categories
          __typename
        }

        fragment localNewsTile on ModularFeedTileLocalNews {
          tileId
          tileType
          localNews {
            ...localNews
            __typename
          }
          __typename
        }

        fragment baseModuleParams on ModularFeedModule {
          moduleId
          collection
          formFactor
          moduleType
          rank
          rowIndex
          searchId
          subTitle
          title
          infoActionPath
          feedIndex
          label
          __typename
        }

        fragment moduleTileParams on ModularFeedTile {
          moduleId
          moduleRank
          moduleType
          __typename
        }

        fragment modularListingTile on ModularFeedTileListing {
          ...listingTile
          ...moduleTileParams
          __typename
        }

        fragment modularBingAdTile on ModularFeedTileBingAd {
          ...bingAdTile
          ...moduleTileParams
          __typename
        }

        fragment modularGoogleDisplayAdTile on ModularFeedTileGoogleDisplayAd {
          ...googleDisplayAdTile
          ...moduleTileParams
          __typename
        }

        fragment modularLocalDisplayAdTile on ModularFeedTileLocalDisplayAd {
          ...localDisplayAdTile
          ...moduleTileParams
          __typename
        }

        fragment modularCustomNativeAdTile on ModularFeedTileCustomNativeAd {
          ...customNativeAdTile
          ...moduleTileParams
          __typename
        }

        fragment modularSellerAdTile on ModularFeedTileSellerAd {
          ...sellerAdTile
          ...moduleTileParams
          __typename
        }

        fragment modularCommunityPostTile on ModularFeedTileCommunityPost {
          ...communityPostTile
          ...moduleTileParams
          __typename
        }

        fragment modularThumbtackServiceTile on ModularFeedTileThumbtackService {
          ...thumbtackServiceTile
          ...moduleTileParams
          __typename
        }

        fragment modularInHouseServiceTile on ModularFeedTileInHouseService {
          ...inHouseServiceTile
          ...moduleTileParams
          __typename
        }

        fragment gridModule on ModularFeedModuleGrid {
          ...baseModuleParams
          grid {
            actionPath
            tiles {
              ...modularListingTile
              ...modularBingAdTile
              ...modularGoogleDisplayAdTile
              ...modularLocalDisplayAdTile
              ...modularCustomNativeAdTile
              ...modularSellerAdTile
              ...modularCommunityPostTile
              ...modularThumbtackServiceTile
              ...modularInHouseServiceTile
              __typename
            }
            __typename
          }
          __typename
        }

        fragment modularFeedResponse on ModularFeedResponse {
          analyticsData {
            requestId
            searchPerformedEventUniqueId
            searchSessionId
            __typename
          }
          categoryInfo {
            categoryId
            isForcedCategory
            __typename
          }
          feedAdditions
          filters {
            ...modularFilterNumericRange
            ...modularFilterSelectionList
            __typename
          }
          looseTiles {
            ...bannerTile
            ...emptyStateTile
            ...listingTile
            ...bingAdTile
            ...googleDisplayAdTile
            ...localDisplayAdTile
            ...adsPostXAdTile
            ...customNativeAdTile
            ...communityPostTile
            ...couponTile
            ...jobTile
            ...localEventTile
            ...sellerAdTile
            ...rentalTile
            ...searchAlertTile
            ...thumbtackServiceTile
            ...inHouseServiceTile
            ...localNewsTile
            __typename
          }
          modules {
            ...gridModule
            __typename
          }
          pageCursor
          query {
            appliedQuery
            decisionType
            originalQuery
            suggestedQuery
            __typename
          }
          requestTimeMetadata {
            resolverComputationTimeSeconds
            serviceRequestTimeSeconds
            totalResolverTimeSeconds
            __typename
          }
          searchAlert {
            alertId
            alertStatus
            searchAlertCount
            __typename
          }
          personalizationPath
          debugInformation @include(if: $debug) {
            rankedListings {
              listingId
              attributes {
                key
                value
                __typename
              }
              __typename
            }
            lastViewedItems {
              listingId
              attributes {
                key
                value
                __typename
              }
              __typename
            }
            categoryAffinities {
              affinity
              count
              decay
              affinityOwner
              __typename
            }
            rankingStats {
              key
              value
              __typename
            }
            modules {
              moduleType
              title
              rank
              value
              __typename
            }
            __typename
          }
          __typename
        }
        """

        variables = {
            "debug": False,
            "searchParams": [
                {"key": "SORT", "value": "newest"},
                {"key": "cid", "value": category_id},
                # {"key": "DISTANCE", "value": "5000"},
                # {"key": "lat", "value": "40.7360524"},
                # {"key": "lon", "value": "-73.9800987"},
                # {"key": "zipcode", "value": "10010"},
            ]
        }

        # Если передан page_cursor, добавляем его в searchParams
        if page_cursor:
            variables["searchParams"].append({"key": "pageCursor", "value": page_cursor})

        # Этот вызов требует аутентификации
        # x-ou-screen указан как "ItemsSearchFeed"
        return await self._make_request(
            "GetModularFeed", query, variables, requires_auth=False, screen="ItemsSearchFeed")

    async def close(self):
        """
        Закрывает aiohttp сессию.
        """
        if self._session and not self._session.closed:
            await self._session.close()


async def test():
    offerup_api = OfferUpAPI(
        proxy = MAIN_PROXY,
    )
    try:
        categories_response = await offerup_api.get_category_taxonomy()
        print(categories_response)
        # parse_response = await offerup_api.get_new_listings_in_category(category_id="1")
        # print(parse_response)
    except Exception as e:
        print(e)
    finally:
        await offerup_api.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
