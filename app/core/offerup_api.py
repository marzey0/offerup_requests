import json
import uuid
from typing import Dict, Any, Optional

import aiohttp


class OfferUpAPI:
    """
    Асинхронный клиент для взаимодействия с API OfferUp.
    Использует aiohttp для выполнения HTTP-запросов.
    """

    BASE_URL = "https://client-graphql.offerup.com/"
    # Пример "жестко закодированного" dummy токена, как видно в запросах
    DUMMY_TOKEN = "dummy"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Инициализирует клиент OfferUpAPI.

        Args:
            session (Optional[aiohttp.ClientSession]): aiohttp сессия.
                                                      Если не указана, будет создана новая.
        """
        self.proxy = "http://a04bd3b5a0c6e395e5cf__cr.us:cc4335faeefde850@gw.dataimpulse.com:823"
        self.session = session or aiohttp.ClientSession()

        # Атрибуты для хранения данных сессии и авторизации, полученных после логина/регистрации
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._session_id: Optional[str] = None
        self._user_id: Optional[str] = None
        self._device_id: Optional[str] = None
        self._user_context: Dict[str, Any] = {}

    def update_auth_tokens(self, jwt_token: str, refresh_token: str):
        """
        Обновляет токены авторизации после логина/регистрации.
        """
        self._jwt_token = jwt_token
        self._refresh_token = refresh_token

    def update_session_data(self, session_id: str, user_id: str, device_id: str):
        """
        Обновляет идентификаторы сессии, пользователя и устройства.
        """
        self._session_id = session_id
        self._user_id = user_id
        self._device_id = device_id

    def update_user_context(self, context: Dict[str, Any]):
        """
        Обновляет словарь user_context.
        """
        self._user_context = context

    def _get_common_headers(self) -> Dict[str, str]:
        """
        Возвращает общие заголовки, которые требуются для большинства запросов.
        """
        headers = {
            "accept": "*/*",
            "user-agent": "OfferUp/2025.42.0 (build: 2025420004; vivo vivo 2019 SP1A.210812.003; Android 12; en_US)",
            "x-ou-version": "2025.42.0",
            "x-ou-device-timezone": "America/New_York",
            "x-ou-d-token": self._device_id or "719062d0720c1500",  # Используем сохраненный или дефолтный
            "Content-Type": "application/json",
            "Host": "client-graphql.offerup.com",
            # Примеры других постоянных заголовков из запросов
            "ou-do-not-sell": "false",
            "ou-device-advertising-id": "427a5b09-585f-4da9-a7d2-4a20ffdcf3c3",
            "ou-browser-user-agent": "Mozilla/5.0 (Linux; Android 12; vivo 2019 Build/SP1A.210812.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.7339.51 Mobile Safari/537.36",
        }
        return headers

    def _get_authenticated_headers(self) -> Dict[str, str]:
        """
        Возвращает заголовки, требующие аутентификации (JWT токен).
        """
        headers = self._get_common_headers()
        if self._jwt_token:
            headers["authorization"] = f"Bearer {self._jwt_token}"
            headers["x-ou-auth-token"] = self.DUMMY_TOKEN
        return headers

    def _build_session_id(self) -> str:
        """
        Помогает сформировать x-ou-session-id как в примерах.
        """
        unique_id = str(uuid.uuid4())
        timestamp = str(int(self.session.timeout.total * 1000)) # Упрощенный timestamp, обычно текущее время
        return f"{self._session_id}@{timestamp}" if self._session_id else f"14b2640b-86d9-4b81-8efb-31b781c5e468@{timestamp}"

    async def _make_request(self, operation_name: str, query: str, variables: Dict[str, Any] = None,
                            requires_auth: bool = False, screen: str = "", additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Внутренний метод для выполнения GraphQL-запросов.

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
            "x-ou-session-id": self._build_session_id(),
            "x-ou-usercontext": json.dumps(self._user_context) if self._user_context else "{}",
            "x-ou-screen": screen,
            # Примеры заголовков, которые могут меняться
            "x-request-id": str(uuid.uuid4()),
            # Sentry заголовки опущены для краткости, но можно добавить
        })

        # Упрощенный URL, так как все запросы идут на один эндпоинт
        url = self.BASE_URL

        payload = {
            "operationName": operation_name,
            "query": query,
        }
        if variables is not None:
            payload["variables"] = variables

        try:
            async with self.session.post(url, headers=headers, json=payload, proxy=self.proxy) as response:
                response.raise_for_status()  # Вызовет исключение для 4xx/5xx
                return await response.json()
        except aiohttp.ClientResponseError as e:
            print(f"HTTP Error {e.status}: {e.message}")
            print(f"Response Body: {await e.response.text()}")
            raise
        except aiohttp.ClientError as e:
            print(f"Client Error: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error during request: {e}")
            raise

    # --- API Методы ---

    async def get_user_context(self, viewport_size: Dict[str, int], search_location: Dict[str, float]) -> Dict[str, Any]:
        """
        Получает контекст пользователя.
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
        # Этот вызов не требует аутентификации
        return await self._make_request("GetUserContext", query, variables, requires_auth=False, screen="OnboardingBuyerInterestSelection")

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
        # Этот вызов не требует аутентификации
        return await self._make_request("Signup", query, variables, requires_auth=False, screen="/auth-stack/signup")

    async def change_phone_number(self, phone_number: str, country_code: int = 1) -> Dict[str, Any]:
        """
        Изменяет номер телефона пользователя.
        """
        query = """
        mutation ChangePhoneNumber($countryCode: Int!, $phoneNumber: String!) {
          changePhoneNumber( {countryCode: $countryCode, phoneNumber: $phoneNumber}) {
            referenceId
            __typename
          }
        }
        """
        variables = {
            "phoneNumber": phone_number,
            "countryCode": country_code
        }
        return await self._make_request("ChangePhoneNumber", query, variables, requires_auth=True, screen="VerifyPhone")

    async def change_phone_number_confirm(self, otp: str, reference_id: str, phone_number: str, country_code: int = 1, challenge_id: str = None) -> Dict[str, Any]:
        """
        Подтверждает изменение номера телефона с помощью OTP-кода.
        """
        query = """
        mutation ChangePhoneNumberConfirm($otp: String!, $referenceId: String!, $countryCode: Int!, $phoneNumber: String!, $challengeId: ID) {
          changePhoneNumberConfirm(
             {otp: $otp, referenceId: $referenceId, countryCode: $countryCode, phoneNumber: $phoneNumber, challengeId: $challengeId}
          )
        }
        """
        variables = {
            "otp": otp,
            "referenceId": reference_id,
            "countryCode": country_code,
            "phoneNumber": phone_number
            # challengeId опционально
        }
        if challenge_id:
            variables["challengeId"] = challenge_id

        return await self._make_request("ChangePhoneNumberConfirm", query, variables, requires_auth=True, screen="EnterCode")

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
        return await self._make_request("GetUnreadAlertCount", query, requires_auth=True, screen="/accountstack/account")

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
            # multifactorHeaderInfo опущен, так как не был в примере
        }
        return await self._make_request("ChangeEmail", query, variables, requires_auth=True, screen="/verify-email-stack/verify-email")

    async def get_item_detail_data_by_listing_id(self, listing_id: str, is_logged_in: bool = True, device_location: Dict[str, float] = None) -> Dict[str, Any]:
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
        return await self._make_request("GetItemDetailDataByListingId", query, variables, requires_auth=is_logged_in, screen="ItemDetail")

    async def item_viewed(self, item_id: str, listing_id: str, seller_id: str, origin: str, source: str,
                          tile_type: str, user_id: str, category_id: str, tile_location: int,
                          shipping: Dict[str, Any], posting: Dict[str, Any], vehicle: Dict[str, Any],
                          seller_type: str, header: Dict[str, Any] = None, mobile_header: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Отправляет событие просмотра товара.
        """
        query = """
        mutation ItemViewed($itemId: ID!, $listingId: ID!, $sellerId: ID!, $header: ItemViewedEventHeader!, $mobileHeader: ItemViewedEventMobileHeader!, $origin: String, $source: String, $tileType: String, $userId: String, $moduleId: ID, $shipping: ShippingInput, $vehicle: VehicleInput, $posting: PostingInput, $tileLocation: Int, $categoryId: String, $moduleType: String, $sellerType: SellerType) {
          itemViewed(
            data: {itemId: $itemId, listingId: $listingId, sellerId: $sellerId, origin: $origin, source: $source, tileType: $tileType, userId: $userId, header: $header, mobileHeader: $mobileHeader, moduleId: $moduleId, shipping: $shipping, vehicle: $vehicle, posting: $posting, tileLocation: $tileLocation, categoryId: $categoryId, moduleType: $moduleType, sellerType: $sellerType}
          )
        }
        """
        variables = {
            "itemId": item_id,
            "listingId": listing_id,
            "sellerId": seller_id,
            "origin": origin,
            "source": source,
            "tileType": tile_type,
            "userId": user_id,
            "categoryId": category_id,
            "tileLocation": tile_location,
            "shipping": shipping,
            "posting": posting,
            "vehicle": vehicle,
            "sellerType": seller_type,
            "header": header or {
                "appVersion": "2025.42.0",
                "deviceId": self._device_id or "719062d0720c1500",
                "origin": "android",
                "timestamp": "2025-11-07T08:46:05.326Z", # Требуется обновление
                "uniqueId": str(uuid.uuid4()), # Требуется генерация
                "userId": user_id,
                "deviceLocation": posting.get("itemLocation", {})
            },
            "mobileHeader": mobile_header or {
                "localTimestamp": "2025-11-07T03:46:05.326Z" # Требуется обновление
            }
        }
        return await self._make_request("ItemViewed", query, variables, requires_auth=True, screen="ItemDetail")

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
        return await self._make_request("PublicProfile", query, variables, requires_auth=True, screen="PublicProfile")

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
        return await self._make_request("GetInboxAlerts", query, variables, requires_auth=True, screen="Inbox")

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
        return await self._make_request("GetChatDiscussion", query, variables, requires_auth=True, screen="Discussion")

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
            # photoUuids и suggestedMessageId опущены, так как не были в примере
        }
        return await self._make_request("PostMessage", query, variables, requires_auth=True, screen="Discussion")

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
        return await self._make_request("PostFirstMessage", query, variables, requires_auth=True, screen="Discussion")

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
        return await self._make_request("UpdateReadDate", query, variables, requires_auth=True, screen="Discussion")

    async def close(self):
        """
        Закрывает aiohttp сессию.
        """
        if self.session and not self.session.closed:
            await self.session.close()
