import Foundation

struct MobilePronunciation: Decodable {
    let word: String
    let uk: String?
    let us: String?
}

struct VocabularyLevel: Decodable {
    let word: String
    let level: String?
}

struct MobileCandidate: Decodable {
    let id: Int
    let text: String
    let annotation: String
    let pronunciation: MobilePronunciation?
    let vocabularyLevels: [VocabularyLevel]?
    let translationSenses: [MobileTranslationSense]?
    let fresh: Bool
}

struct VocabularyTag: Decodable {
    let id: String
    let label: String
    let selected: Bool
    let sources: [String]
}
struct MobileTranslationSense: Decodable {
    let index: Int
    let text: String
    let partOfSpeech: String?
    let reading: String?
    let fresh: Bool
    let tags: [VocabularyTag]
    let pronunciation: MobilePronunciation?
}

struct MobileState: Decodable {
    let revision: UInt64
    let input: String
    let preedit: String
    let candidates: [MobileCandidate]
    let commit: String?
    let deleteBackward: Bool
    let english: Bool
    let language: String
    let page: Int
    let pageCount: Int
}

struct MobileResponse: Decodable {
    let handle: UInt64
    let state: MobileState?
    let error: String?
}
