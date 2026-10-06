import Foundation
import WordtrailCore

final class MobileEngine {
    private let queue = DispatchQueue(label: "org.wordtrail.engine", qos: .userInitiated)
    private var handle: UInt64 = 0

    private static func request(_ fields: [String: Any]) throws -> MobileResponse {
        let bytes = try JSONSerialization.data(withJSONObject: fields)
        guard let json = String(data: bytes, encoding: .utf8) else {
            throw NSError(domain: "Wordtrail", code: 1)
        }
        let pointer = json.withCString { qjm_request($0) }
        guard let pointer else { throw NSError(domain: "Wordtrail", code: 2) }
        defer { qjm_string_free(pointer) }
        let output = String(cString: pointer)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let response = try decoder.decode(MobileResponse.self, from: Data(output.utf8))
        if let error = response.error {
            throw NSError(domain: "Wordtrail", code: 3, userInfo: [NSLocalizedDescriptionKey: error])
        }
        return response
    }

    func perform(_ fields: [String: Any], completion: @escaping (Result<MobileState, Error>) -> Void) {
        queue.async { [self] in
            do {
                if handle == 0 {
                    let data = Bundle.main.bundleURL.appendingPathComponent("Data")
                    let user = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true).appendingPathComponent("Learning")
                    let response = try Self.request([
                        "op": "create", "data_dir": data.path, "user_dir": user.path,
                        "language": UserDefaults.standard.string(forKey: "learningLanguage") ?? "en",
                        "vocabulary_targets": UserDefaults.standard.stringArray(forKey: "vocabularyTargets") ?? []
                    ])
                    handle = response.handle
                }
                var request = fields
                request["handle"] = handle
                let response = try Self.request(request)
                if let state = response.state {
                    DispatchQueue.main.async { completion(.success(state)) }
                }
            } catch {
                DispatchQueue.main.async { completion(.failure(error)) }
            }
        }
    }

    deinit {
        let previous = handle
        if previous != 0 {
            queue.async { _ = try? Self.request(["op": "destroy", "handle": previous]) }
        }
    }
}
